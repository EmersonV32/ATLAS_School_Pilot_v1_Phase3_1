"""Dependency container.

A single place that constructs and holds shared components, so real Jetson
modules can replace mocks by swapping what the container builds. Phase 1
wired settings + logger; Phase 2 adds the embedder, vector store, keyword
store, and the hybrid retriever. Vision, audio, LLM, and hardware follow the
same dependency-injection pattern in later phases.
"""

from __future__ import annotations

from pathlib import Path

from atlas.config.loader import load_settings
from atlas.config.settings import Settings
from atlas.models.enums import RunMode
from atlas.storage.event_logger import EventLogger


class Container:
    """Lazily-built application components."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._logger: EventLogger | None = None
        self._embedder = None
        self._vector_store = None
        self._fts_store = None
        self._retriever = None
        self._llm_client = None
        self._dialogue_engine = None
        self._camera_source = None
        self._vision_detector = None
        self._artwork_tracker = None
        self._manual_artwork_capture = None
        self._stt = None
        self._tts = None
        self._hardware = None
        self._session_runner = None

    @property
    def logger(self) -> EventLogger:
        if self._logger is None:
            self._logger = EventLogger(
                logs_dir=self.settings.paths.logs_dir,
                settings=self.settings.logging,
            )
        return self._logger

    # --- Phase 2: retrieval --------------------------------------------
    @property
    def embedder(self):
        if self._embedder is None:
            from atlas.rag.embeddings import make_embedder

            self._embedder = make_embedder(
                self.settings.rag, mock=(self.settings.mode == RunMode.DEV)
            )
        return self._embedder

    @property
    def vector_store(self):
        if self._vector_store is None:
            from atlas.rag.ingest import build_vector_store

            self._vector_store = build_vector_store(self.settings)
        return self._vector_store

    @property
    def fts_store(self):
        if self._fts_store is None:
            from atlas.rag.sqlite_fts_store import SqliteFtsStore

            db_path = Path(self.settings.paths.sqlite_dir) / "atlas.db"
            self._fts_store = SqliteFtsStore(db_path)
        return self._fts_store

    def _artwork_titles(self) -> dict[str, str]:
        """Load artwork_id -> title from the default pack, if present."""
        from atlas.rag.ingest import load_content_pack

        pack_dir = (
            Path(self.settings.paths.content_packs_dir) / self.settings.default_pack_id
        )
        if not (pack_dir / "manifest.json").exists():
            return {}
        try:
            pack = load_content_pack(pack_dir)
        except Exception:
            return {}
        return {a.artwork_id: a.title for a in pack.artworks}

    @property
    def retriever(self):
        if self._retriever is None:
            from atlas.rag.retriever import HybridRetriever

            self._retriever = HybridRetriever(
                embedder=self.embedder,
                vector_store=self.vector_store,
                fts_store=self.fts_store,
                settings=self.settings.rag,
                artwork_titles=self._artwork_titles(),
            )
        return self._retriever

    # --- Phase 3: dialogue ---------------------------------------------
    @property
    def llm_client(self):
        if self._llm_client is None:
            llm = self.settings.llm
            use_cloud_llm = (
                llm.provider in {"gemini", "openai", "kimi"}
                and llm.cloud_llm_enabled
                and self.settings.mode in (RunMode.DEVICE, RunMode.DEMO)
            )
            if use_cloud_llm and llm.provider == "gemini":
                from atlas.dialogue.gemini_client import GeminiClient

                self._llm_client = GeminiClient(
                    model=llm.model,
                    api_key_env=llm.gemini_api_key_env,
                )
            elif use_cloud_llm:
                from atlas.dialogue.openai_compatible_client import (
                    OpenAICompatibleClient,
                )

                is_kimi = llm.provider == "kimi"
                self._llm_client = OpenAICompatibleClient(
                    provider_name="Kimi" if is_kimi else "OpenAI",
                    model=llm.model,
                    api_key_env=(
                        llm.kimi_api_key_env if is_kimi else llm.openai_api_key_env
                    ),
                    base_url=llm.kimi_base_url if is_kimi else None,
                    timeout_s=llm.timeout_s,
                )
            else:
                from atlas.dialogue.mock_llm_client import MockLLMClient

                self._llm_client = MockLLMClient()
        return self._llm_client

    @property
    def dialogue_engine(self):
        if self._dialogue_engine is None:
            from atlas.dialogue.dialogue_engine import DialogueEngine

            use_cloud_llm = (
                self.settings.llm.provider in {"gemini", "openai", "kimi"}
                and self.settings.llm.cloud_llm_enabled
                and self.settings.mode in (RunMode.DEVICE, RunMode.DEMO)
            )
            self._dialogue_engine = DialogueEngine(
                llm_client=self.llm_client, expect_json=use_cloud_llm
            )
        return self._dialogue_engine

    # --- Phase 4: perception, speech, hardware, pipeline ---------------
    @property
    def camera_source(self):
        if self._camera_source is None:
            from atlas.vision.camera_source import CameraSource

            hw = self.settings.hardware
            self._camera_source = CameraSource(
                source=hw.camera_source,
                width=hw.camera_width,
                height=hw.camera_height,
                fps=hw.camera_fps,
                rotation_degrees=hw.camera_rotation_degrees,
                reconnect_s=hw.camera_reconnect_s,
            )
        return self._camera_source

    @property
    def vision_detector(self):
        if self._vision_detector is None:
            if self.settings.mode == RunMode.DEVICE:
                from pathlib import Path

                from atlas.vision.yolo_detector import YoloDetector

                hw = self.settings.hardware
                use_engine = hw.yolo_backend == "tensorrt" or (
                    hw.yolo_backend == "auto"
                    and Path(hw.yolo_tensorrt_path).is_file()
                )
                model_path = (
                    hw.yolo_tensorrt_path if use_engine else hw.yolo_model_path
                )
                fallback_path = hw.yolo_model_path if use_engine else None
                self._vision_detector = YoloDetector(
                    model_path=model_path,
                    conf_threshold=hw.vision_conf_threshold,
                    mask_conf_threshold=hw.vision_mask_conf_threshold,
                    center_weight=hw.vision_center_weight,
                    image_size=hw.yolo_imgsz,
                    fallback_model_path=fallback_path,
                )
            else:
                from atlas.vision.mock_detector import MockDetector

                self._vision_detector = MockDetector()
        return self._vision_detector

    @property
    def artwork_tracker(self):
        if self._artwork_tracker is None:
            from atlas.vision.tracker import ArtworkTracker

            titles = self._artwork_titles()
            self._artwork_tracker = ArtworkTracker(
                detector=self.vision_detector,
                conf_threshold=self.settings.hardware.vision_conf_threshold,
                stability_frames=3,
                allow_last_stable=(self.settings.mode != RunMode.DEVICE),
                valid_artwork_ids=set(titles) or None,
            )
        return self._artwork_tracker

    @property
    def manual_artwork_capture(self):
        if self._manual_artwork_capture is None:
            enabled = (
                self.settings.hardware.manual_capture_enabled
                and self.settings.llm.provider == "gemini"
                and self.settings.llm.cloud_llm_enabled
                and self.settings.mode in (RunMode.DEVICE, RunMode.DEMO)
            )
            if not enabled:
                return None

            from atlas.vision.manual_capture import ManualArtworkCapture

            hardware = self.settings.hardware
            self._manual_artwork_capture = ManualArtworkCapture(
                client=self.llm_client,
                candidates=self._artwork_titles(),
                crop_ratio=hardware.manual_capture_crop_ratio,
                jpeg_quality=hardware.manual_capture_jpeg_quality,
            )
        return self._manual_artwork_capture

    @property
    def stt(self):
        if self._stt is None:
            if self.settings.mode == RunMode.DEVICE:
                from atlas.audio.whisper_stt import WhisperSTT

                offline_stt = WhisperSTT(
                    model_size=self.settings.hardware.whisper_model_size,
                    device=self.settings.hardware.whisper_device,
                    compute_type=self.settings.hardware.whisper_compute_type,
                    input_device_name=self.settings.hardware.headset_name,
                    sample_rate=self.settings.hardware.audio_sample_rate,
                    channels=self.settings.hardware.audio_channels,
                    beam_size=self.settings.hardware.whisper_beam_size,
                    local_files_only=(
                        self.settings.hardware.whisper_local_files_only
                    ),
                )
                speech = self.settings.speech
                use_deepgram = (
                    speech.stt_provider == "deepgram"
                    and speech.cloud_speech_enabled
                )
                if use_deepgram:
                    from atlas.audio.deepgram_stt import DeepgramSTT
                    from atlas.audio.fallback import FallbackSTT

                    cloud_stt = DeepgramSTT(
                        api_key_env=speech.deepgram_api_key_env,
                        model=speech.deepgram_model,
                        language=speech.deepgram_language,
                        input_device_name=self.settings.hardware.headset_name,
                        sample_rate=self.settings.hardware.audio_sample_rate,
                        channels=self.settings.hardware.audio_channels,
                        endpointing_ms=speech.deepgram_endpointing_ms,
                        vad_threshold=speech.silero_threshold,
                        silero_model_path=speech.silero_model_path,
                        min_speech_ms=speech.silero_min_speech_ms,
                        min_silence_ms=speech.silero_min_silence_ms,
                        pre_roll_ms=speech.silero_pre_roll_ms,
                        final_timeout_s=speech.deepgram_final_timeout_s,
                        keyterms=speech.deepgram_keyterms,
                        log_live_transcripts=(
                            self.settings.logging.log_live_stt
                        ),
                    )
                    self._stt = (
                        FallbackSTT(cloud_stt, offline_stt)
                        if speech.offline_fallback_enabled
                        else cloud_stt
                    )
                else:
                    self._stt = offline_stt
            else:
                from atlas.audio.mock_stt import MockSTT

                self._stt = MockSTT()
        return self._stt

    @property
    def tts(self):
        if self._tts is None:
            if self.settings.mode == RunMode.DEVICE:
                from atlas.audio.piper_tts import PiperTTS

                output_name = (
                    self.settings.hardware.audio_output_name
                    or self.settings.hardware.headset_name
                )
                offline_tts = PiperTTS(
                    voice_en=self.settings.hardware.piper_voice_en,
                    voice_fr=self.settings.hardware.piper_voice_fr,
                    voice_es=self.settings.hardware.piper_voice_es,
                    voice_it=self.settings.hardware.piper_voice_it,
                    voice_zh=self.settings.hardware.piper_voice_zh,
                    piper_binary=self.settings.hardware.piper_binary_path or "piper",
                    output_device_name=output_name,
                )
                speech = self.settings.speech
                use_cartesia = (
                    speech.tts_provider == "cartesia"
                    and speech.cloud_speech_enabled
                )
                if use_cartesia:
                    from atlas.audio.cartesia_tts import CartesiaTTS
                    from atlas.audio.fallback import FallbackTTS

                    cloud_tts = CartesiaTTS(
                        api_key_env=speech.cartesia_api_key_env,
                        model=speech.cartesia_model,
                        voice_id=speech.cartesia_voice_id,
                        api_version=speech.cartesia_api_version,
                        output_device_name=output_name,
                        sample_rate=speech.cartesia_sample_rate,
                        response_timeout_s=speech.cartesia_response_timeout_s,
                    )
                    self._tts = (
                        FallbackTTS(cloud_tts, offline_tts)
                        if speech.offline_fallback_enabled
                        else cloud_tts
                    )
                else:
                    self._tts = offline_tts
            else:
                from atlas.audio.mock_tts import MockTTS

                self._tts = MockTTS()
        return self._tts

    @property
    def hardware(self):
        if self._hardware is None:
            use_ev3 = (
                self.settings.mode == RunMode.DEVICE
                and self.settings.hardware.enable_ev3
                and self.settings.hardware.ev3_bt_address
            )
            if use_ev3:
                from atlas.hardware.ev3_hardware import EV3Hardware

                self._hardware = EV3Hardware(
                    bt_address=self.settings.hardware.ev3_bt_address,
                    mailbox_name=self.settings.hardware.ev3_mailbox_name,
                    connect_timeout_s=(self.settings.hardware.ev3_connect_timeout_s),
                    status_led_enabled=(self.settings.hardware.ev3_status_led_enabled),
                )
            else:
                from atlas.hardware.mock_hardware import MockHardware

                self._hardware = MockHardware()
        return self._hardware

    @property
    def session_runner(self):
        if self._session_runner is None:
            from atlas.pipeline.session_runner import SessionRunner, make_retriever

            self._session_runner = SessionRunner(
                detector=self.artwork_tracker,
                stt=self.stt,
                tts=self.tts,
                hardware=self.hardware,
                dialogue_engine=self.dialogue_engine,
                retriever=make_retriever(self.retriever),
                manual_capture=self.manual_artwork_capture,
                listen_duration_s=self.settings.speech.listen_duration_s,
                # Never split one visitor response over multiple synthesis
                # requests. A continuous Cartesia stream can fall back or
                # shift timbre between segments, which is worse than waiting
                # briefly for Gemini's short complete answer.
                stream_responses=False,
                log_transcripts=self.settings.logging.log_transcripts,
                log_llm_responses=(
                    self.settings.logging.log_llm_responses
                ),
            )
        return self._session_runner

    def close(self) -> None:
        """Release camera and Bluetooth resources."""
        if self._camera_source is not None:
            self._camera_source.stop()
        if self._stt is not None:
            self._stt.close()
        if self._tts is not None:
            self._tts.close()
        if self._hardware is not None:
            self._hardware.close()

    # --- Extension points (filled in later phases) ----------------------
    # self.vision_detector   -> VisionDetector (mock/yolo)   [Phase 4]
    # self.stt               -> STTBase (mock/whisper)       [Phase 4]
    # self.tts               -> TTSBase (mock/piper)         [Phase 4]
    # self.llm_client        -> LLMBase (mock/gemini)        [Phase 3]
    # self.hardware          -> HardwareController (mock/ev3)[Phase 4]


def build_container(config_dir: str | Path = "config") -> Container:
    """Construct a Container from on-disk configuration."""
    settings = load_settings(config_dir)
    return Container(settings)
