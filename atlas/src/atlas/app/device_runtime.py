"""Continuous real-hardware runtime for ATLAS on the Jetson."""

from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from atlas.app.dependency_container import Container
from atlas.app.headset_button import HeadsetButtonListener
from atlas.audio.stt import TranscriptResult
from atlas.vision.detector import ArtworkDetection

logger = logging.getLogger(__name__)

class VisionHold:
    """Accumulate a centered gaze while tolerating brief detector flicker."""

    def __init__(self, hold_seconds: float, gap_tolerance_s: float) -> None:
        self.hold_seconds = hold_seconds
        self.gap_tolerance_s = gap_tolerance_s
        self.candidate_id: str | None = None
        self.candidate_since = 0.0
        self.last_seen = 0.0

    def reset(self) -> None:
        self.candidate_id = None
        self.candidate_since = 0.0
        self.last_seen = 0.0

    def observe(
        self,
        detection: ArtworkDetection | None,
        *,
        centered: bool,
        now: float | None = None,
    ) -> bool:
        now = time.monotonic() if now is None else now
        if (
            self.candidate_id is not None
            and now - self.last_seen > self.gap_tolerance_s
        ):
            self.reset()

        if detection is None or not centered:
            return False

        if self.candidate_id is None:
            self.candidate_id = detection.artwork_id
            self.candidate_since = now
            self.last_seen = now
            return False

        if detection.artwork_id != self.candidate_id:
            return False

        self.last_seen = now
        return now - self.candidate_since >= self.hold_seconds

    def held_seconds(self, now: float | None = None) -> float:
        if self.candidate_id is None:
            return 0.0
        now = time.monotonic() if now is None else now
        return max(0.0, now - self.candidate_since)


class ContinuousQuestionListener:
    """Keep STT active while a dashboard session is active.

    Only microphone capture runs here. RAG, Gemini, TTS, and SQLite-backed
    retrieval stay on the device runtime thread.
    """

    def __init__(self, runner) -> None:
        self._runner = runner
        self._active = threading.Event()
        self._response_finished = threading.Event()
        self._response_finished.set()
        self._stop = threading.Event()
        self._questions: queue.Queue[TranscriptResult] = queue.Queue(maxsize=1)
        self._thread = threading.Thread(
            target=self._run,
            name="atlas-continuous-listener",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def activate(self) -> None:
        self._active.set()

    def deactivate(self) -> None:
        self._active.clear()
        while True:
            try:
                self._questions.get_nowait()
            except queue.Empty:
                break
        self._response_finished.set()

    def response_finished(self) -> None:
        self._response_finished.set()

    def pop(self) -> TranscriptResult | None:
        try:
            return self._questions.get_nowait()
        except queue.Empty:
            return None

    def stop(self) -> None:
        self._stop.set()
        self._active.set()
        self._response_finished.set()
        if self._thread.is_alive():
            self._thread.join(timeout=6.0)

    def _run(self) -> None:
        while not self._stop.is_set():
            if not self._active.wait(timeout=0.2):
                continue
            if not self._response_finished.wait(timeout=0.2):
                continue
            if self._stop.is_set() or not self._active.is_set():
                continue
            try:
                transcript = self._runner.listen_once(play_cue=False)
            except Exception as exc:
                logger.exception("[Listening] Continuous STT failure: %s", exc)
                time.sleep(0.5)
                continue
            if transcript is None or not transcript.text.strip():
                continue
            if not self._active.is_set():
                continue
            self._response_finished.clear()
            try:
                self._questions.put(transcript, timeout=0.5)
            except queue.Full:
                logger.warning("[Listening] Dropped question because one is pending")
                self._response_finished.set()


class DeviceRuntime:
    def __init__(self, container: Container) -> None:
        self.container = container
        self.settings = container.settings.hardware
        self._capture_requested = threading.Event()
        self._button_actions: queue.Queue[int] = queue.Queue()
        self._headset_button: HeadsetButtonListener | None = None
        self._dashboard_server = None
        self._dashboard_thread: threading.Thread | None = None
        self._dashboard_service = None

    def request_manual_capture(self) -> None:
        """Adapter point for terminal input now and the Shokz button later."""
        self._capture_requested.set()

    def _queue_button_action(self, clicks: int) -> None:
        self._button_actions.put(clicks)

    def _handle_headset_button(self, clicks: int) -> bool:
        """Map every detected Shokz button gesture to a capture request.

        The device uses its play/pause key as one simple visitor-facing action.
        Click aggregation remains enabled to avoid an accidental duplicate event,
        but a single, double, or triple press always results in one capture.
        """
        if clicks <= 0:
            return False
        self.request_manual_capture()
        logger.info(
            "[Button] Manual artwork capture requested [clicks=%d action=%s]",
            clicks,
            self.settings.headset_button_action,
        )
        print("[Button] Manual artwork capture requested")
        return True

    def _start_headset_button_listener(self) -> str:
        if not self.settings.headset_button_enabled:
            return "disabled"
        self._headset_button = HeadsetButtonListener(
            self._queue_button_action,
            device_path=self.settings.headset_button_device,
            device_name="Shokz",
            key_code=self.settings.headset_button_key_code,
            click_window_s=self.settings.headset_button_click_window_s,
        )
        return self._headset_button.start()

    def _stop_headset_button_listener(self) -> None:
        if self._headset_button is not None:
            self._headset_button.stop()

    def _start_terminal_capture_listener(self) -> None:
        if not self.settings.manual_capture_keyboard_enabled or not sys.stdin.isatty():
            return

        def listen() -> None:
            while True:
                try:
                    command = input().strip().lower()
                except (EOFError, OSError):
                    return
                if command in {"c", "capture"}:
                    self.request_manual_capture()

        threading.Thread(
            target=listen,
            name="atlas-terminal-capture",
            daemon=True,
        ).start()

    def _start_dashboard(self) -> str:
        dashboard = getattr(self.container.settings, "dashboard", None)
        if dashboard is None or not dashboard.enabled:
            return "disabled"

        import uvicorn

        from atlas.dashboard.api import create_app

        app = create_app(
            self.container,
            capture_request=self.request_manual_capture,
        )
        self._dashboard_service = app.state.service
        config = uvicorn.Config(
            app,
            host=dashboard.host,
            port=dashboard.port,
            log_level="warning",
            access_log=False,
        )
        self._dashboard_server = uvicorn.Server(config)
        self._dashboard_thread = threading.Thread(
            target=self._dashboard_server.run,
            name="atlas-dashboard",
            daemon=True,
        )
        self._dashboard_thread.start()

        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if self._dashboard_server.started:
                return f"ready at http://{dashboard.host}:{dashboard.port}"
            if not self._dashboard_thread.is_alive():
                break
            time.sleep(0.05)
        raise RuntimeError("dashboard server did not start")

    def _stop_dashboard(self) -> None:
        if self._dashboard_server is not None:
            self._dashboard_server.should_exit = True
        if self._dashboard_thread and self._dashboard_thread.is_alive():
            self._dashboard_thread.join(timeout=5.0)

    def preload(self) -> dict[str, str]:
        """Load all local models/adapters before announcing readiness."""
        camera = self.container.camera_source
        # The reader owns reconnection. Keep speech and the dashboard available
        # while a Wi-Fi camera is returning to the network.
        try:
            camera.start(timeout_s=10.0)
            camera_status = "ready"
        except RuntimeError as exc:
            camera_status = f"recovering: {exc}"
            logger.warning(
                "Camera startup deferred; reader will keep retrying: %s", exc
            )

        # SQLite connections belong to the thread that creates them. Load both
        # the index and the real embedding model here, so the first visitor
        # never pays the multi-second model-load cost.
        statuses: dict[str, str] = {"Camera": camera_status}
        try:
            self.container.embedder.embed_one("ATLAS museum guide startup warm-up")
            _ = self.container.retriever
            statuses["RAG"] = "ready"
            logger.info("[RAG] Embedding model warmed before visitor sessions")
        except Exception as exc:
            statuses["RAG"] = f"unavailable: {exc}"
            logger.warning("RAG preload failed: %s", exc)

        jobs: dict[str, Callable[[], object]] = {
            "YOLO": lambda: self.container.vision_detector.warm_up(),
            "STT": lambda: self.container.stt.warm_up(),
            "TTS": lambda: self.container.tts.warm_up(),
        }
        llm = getattr(self.container.settings, "llm", None)
        if (
            llm is not None
            and llm.provider == "gemini"
            and llm.cloud_llm_enabled
        ):
            jobs["Gemini"] = lambda: self.container.llm_client.warm_up()
        else:
            statuses["Gemini"] = "mock (cloud disabled)"
        if self.container.settings.hardware.enable_ev3:
            jobs["EV3"] = lambda: self.container.hardware.warm_up()

        workers = min(4, len(jobs))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(job): name for name, job in jobs.items()}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    future.result()
                    statuses[name] = "ready"
                except Exception as exc:
                    statuses[name] = f"unavailable: {exc}"
                    logger.warning("%s preload failed: %s", name, exc)
        providers = (
            ("STT", self.container.stt),
            ("TTS", self.container.tts),
        )
        for name, provider in providers:
            provider_status = getattr(provider, "provider_status", None)
            description = (
                provider_status()
                if callable(provider_status)
                else type(provider).__name__
            )
            logger.info(
                "[Provider] %s: %s",
                name,
                description,
            )
        return statuses

    def _required_components(self) -> tuple[str, ...]:
        """Return components that must be ready before the voice experience starts."""
        required = ("YOLO", "STT", "TTS", "RAG")
        llm = getattr(self.container.settings, "llm", None)
        if (
            llm is not None
            and llm.provider == "gemini"
            and llm.cloud_llm_enabled
        ):
            required += ("Gemini",)
        return required

    def run(
        self,
        max_interactions: int = 0,
        wait_for_terminal: bool = False,
    ) -> None:
        statuses = self.preload()
        required = self._required_components()
        failed = [name for name in required if statuses.get(name) != "ready"]
        if failed:
            raise RuntimeError("required components unavailable: " + ", ".join(failed))

        try:
            statuses["Dashboard"] = self._start_dashboard()
        except Exception as exc:
            statuses["Dashboard"] = f"unavailable: {exc}"
            logger.warning("Dashboard startup failed: %s", exc)
        statuses["Button"] = self._start_headset_button_listener()

        print("\n[Startup] ATLAS device runtime preload complete")
        for name in (
            "Camera",
            "YOLO",
            "STT",
            "TTS",
            "RAG",
            "Gemini",
            "EV3",
            "Dashboard",
            "Button",
        ):
            if name in statuses:
                print(f"  {name:<10} {statuses[name]}")

        if wait_for_terminal:
            input("\nATLAS is fully loaded. Press Enter to begin listening... ")
        self._start_terminal_capture_listener()
        print(
            "\n[Ready] Start a dashboard session and speak at any time. "
            "Ctrl+C stops."
        )
        if self.settings.manual_capture_keyboard_enabled:
            print(
                "[Ready] Type c then Enter to identify the centered artwork manually."
            )

        tracker = self.container.artwork_tracker
        runner = self.container.session_runner
        camera = self.container.camera_source
        listener = ContinuousQuestionListener(runner)
        listener.start()
        vision_hold = VisionHold(
            self.settings.vision_hold_seconds,
            self.settings.vision_gap_tolerance_s,
        )
        latched_id: str | None = None
        active_detection: ArtworkDetection | None = None
        clear_count = 0
        completed = 0
        last_frame_number = 0
        last_missing_frame_log_at = 0.0
        active_session_id: str | None = None

        try:
            while max_interactions <= 0 or completed < max_interactions:
                frame, last_frame_number = camera.wait_for_new_frame(
                    after_number=last_frame_number,
                    timeout_s=2.0,
                )
                if frame is None:
                    now = time.monotonic()
                    if now - last_missing_frame_log_at >= 10.0:
                        camera_status = camera.status()
                        logger.warning(
                            "No fresh camera frame; still recovering "
                            "[ready=%s error=%s]",
                            camera_status.get("ready"),
                            camera_status.get("last_error") or "none",
                        )
                        last_missing_frame_log_at = now
                    continue

                detection = tracker.update(frame)
                dashboard_session_id = (
                    self._dashboard_service.session_id
                    if self._dashboard_service is not None
                    else "standalone"
                )
                if dashboard_session_id is None:
                    listener.deactivate()
                    self._capture_requested.clear()
                    while True:
                        try:
                            self._button_actions.get_nowait()
                        except queue.Empty:
                            break
                    vision_hold.reset()
                    latched_id = None
                    active_detection = None
                    clear_count = 0
                    active_session_id = None
                    time.sleep(self.settings.vision_poll_interval_s)
                    continue

                if self._dashboard_service is not None:
                    runner.set_preferred_language(self._dashboard_service.language)
                    runner.set_preferred_profile(self._dashboard_service.profile)

                if dashboard_session_id != active_session_id:
                    active_session_id = dashboard_session_id
                    vision_hold.reset()
                    latched_id = None
                    active_detection = None
                    clear_count = 0
                    print(f"[Session] Active: {active_session_id}")
                    runner.cue_listening()
                    listener.activate()
                    logger.info(
                        "[Listening] Always-ready STT active; vision supplies context"
                    )

                try:
                    button_clicks = self._button_actions.get_nowait()
                except queue.Empty:
                    button_clicks = 0
                self._handle_headset_button(button_clicks)

                if self._capture_requested.is_set():
                    self._capture_requested.clear()
                    print("[Capture] Identifying the centered artwork...")
                    result = runner.capture_context(
                        frame,
                        (
                            self._dashboard_service.language
                            if self._dashboard_service is not None
                            else "en"
                        ),
                        announce=False,
                    )
                    if result.success:
                        latched_id = result.detection.artwork_id
                        active_detection = result.detection
                        clear_count = 0
                        print(
                            "[Capture] Context selected: "
                            f"{result.detection.label}; listening remains active"
                        )
                    else:
                        print(f"[Capture] Stopped: {result.error}")
                    vision_hold.reset()
                    continue

                question = listener.pop()
                if question is not None:
                    try:
                        result = runner.respond_to_transcript(
                            question,
                            frame=frame,
                            detection=active_detection,
                        )
                        if (
                            result.event == "language_changed"
                            and result.transcript is not None
                            and self._dashboard_service is not None
                        ):
                            self._dashboard_service.set_profile(
                                language=result.transcript.language
                            )
                            logger.info(
                                "[Language] Dashboard synchronized to %s",
                                result.transcript.language,
                            )
                        if result.success:
                            completed += 1
                            if result.detection is not None:
                                active_detection = result.detection
                                latched_id = result.detection.artwork_id
                            print(f"[Cycle] Complete ({completed})")
                        else:
                            print(f"[Cycle] Stopped: {result.error}")
                    finally:
                        listener.response_finished()
                    vision_hold.reset()
                    continue

                centered = bool(
                    detection
                    and detection.stable
                    and detection.center_score is not None
                    and detection.center_score >= self.settings.vision_center_threshold
                )

                if latched_id is not None:
                    still_seen = bool(
                        centered and detection and detection.artwork_id == latched_id
                    )
                    clear_count = 0 if still_seen else clear_count + 1
                    if clear_count >= self.settings.vision_clear_frames:
                        print("[Vision] Gaze cleared; ready for another artwork")
                        latched_id = None
                        active_detection = None
                        clear_count = 0
                        self.container.hardware.reset_exhibit()
                    time.sleep(self.settings.vision_poll_interval_s)
                    continue

                previous_candidate = vision_hold.candidate_id
                triggered = vision_hold.observe(detection, centered=centered)
                if not centered or detection is None:
                    time.sleep(self.settings.vision_poll_interval_s)
                    continue

                if vision_hold.candidate_id != previous_candidate:
                    print(
                        f"[Vision] Holding {detection.label} "
                        f"({detection.confidence:.0%}, "
                        f"center={detection.center_score:.2f})"
                    )
                    continue

                if not triggered:
                    continue

                held_s = vision_hold.held_seconds()
                print(f"[Vision] Triggered {detection.label} after {held_s:.1f}s")
                active_detection = detection
                latched_id = detection.artwork_id
                clear_count = 0
                self.container.hardware.focus_artwork(detection.artwork_id)
                logger.info(
                    "[Vision] Artwork context selected; continuous listening unchanged"
                )
                vision_hold.reset()
        finally:
            try:
                self._stop_headset_button_listener()
            finally:
                try:
                    listener.stop()
                finally:
                    try:
                        self.container.hardware.reset_exhibit()
                    finally:
                        try:
                            self._stop_dashboard()
                        finally:
                            self.container.close()
