"""Hardware-independent tests for the Jetson device adapters."""

from __future__ import annotations

import os
import struct
import sys
import threading
import time
from types import SimpleNamespace

from atlas.app.dependency_container import Container
from atlas.app.device_runtime import (
    DEMO_VISION_HOLD_SECONDS,
    ContinuousQuestionListener,
    DeviceRuntime,
    VisionHold,
)
from atlas.audio.devices import (
    configure_pulse_capture,
    device_name_score,
    find_pulse_defaults,
    find_sounddevice_input,
    parse_pactl_defaults,
    select_pulse_device,
)
from atlas.audio.stt import TranscriptResult
from atlas.audio.whisper_stt import WhisperSTT
from atlas.config.loader import load_settings
from atlas.config.settings import DashboardSettings, Settings
from atlas.hardware.ev3_hardware import EV3Hardware, _MailboxClient
from atlas.vision.camera_source import normalize_camera_source
from atlas.vision.detector import ArtworkDetection
from atlas.vision.yolo_detector import (
    YoloDetector,
    bbox_center_score,
    normalize_yolo_label,
)


def test_camera_source_accepts_usb_index_and_url():
    assert normalize_camera_source("0") == 0
    assert normalize_camera_source(2) == 2
    url = "http://192.168.1.42:81/stream"
    assert normalize_camera_source(url) == url


def test_pulse_defaults_fail_closed_when_pactl_is_unavailable(monkeypatch):
    def missing_pactl(*_args, **_kwargs):
        raise OSError("pactl is unavailable")

    monkeypatch.setattr("atlas.audio.devices.subprocess.run", missing_pactl)
    assert find_pulse_defaults() == {}


def test_whisper_fallback_defaults_to_cached_files_only():
    stt = WhisperSTT()
    assert stt._local_files_only is True


def test_device_runtime_can_disable_integrated_dashboard():
    container = SimpleNamespace(
        settings=SimpleNamespace(
            hardware=SimpleNamespace(),
            dashboard=SimpleNamespace(enabled=False),
        )
    )
    runtime = DeviceRuntime(container)
    assert runtime._start_dashboard() == "disabled"


def test_continuous_listener_pauses_until_response_finishes():
    class FakeRunner:
        def __init__(self):
            self.calls = 0
            self.play_cues = []

        def listen_once(self, *, play_cue=False):
            self.calls += 1
            self.play_cues.append(play_cue)
            return TranscriptResult(f"question {self.calls}", "en")

    runner = FakeRunner()
    listener = ContinuousQuestionListener(runner)
    listener.start()
    listener.activate()
    try:
        deadline = time.monotonic() + 1.0
        first = None
        while first is None and time.monotonic() < deadline:
            first = listener.pop()
            time.sleep(0.01)
        assert first is not None
        assert first.text == "question 1"
        time.sleep(0.05)
        assert runner.calls == 1

        listener.response_finished()
        deadline = time.monotonic() + 1.0
        second = None
        while second is None and time.monotonic() < deadline:
            second = listener.pop()
            time.sleep(0.01)
        assert second is not None
        assert second.text == "question 2"
        assert runner.play_cues == [False, False]
    finally:
        listener.stop()


def test_continuous_listener_runs_proactive_prompt_between_listens():
    prompt_ran = threading.Event()

    class FakeRunner:
        def listen_once(self, *, play_cue=False):
            time.sleep(0.01)
            return None

    listener = ContinuousQuestionListener(FakeRunner())
    listener.start()
    listener.activate()
    listener.request_prompt(prompt_ran.set)
    try:
        assert prompt_ran.wait(timeout=1.0)
    finally:
        listener.stop()


def test_demo_artwork_hold_is_exactly_five_seconds():
    hold = VisionHold(
        hold_seconds=DEMO_VISION_HOLD_SECONDS,
        gap_tolerance_s=0.8,
    )
    detection = _centered_detection()
    assert DEMO_VISION_HOLD_SECONDS == 5.0
    assert not hold.observe(detection, centered=True, now=100.0)
    for offset in range(1, 10):
        assert not hold.observe(detection, centered=True, now=100.0 + offset * 0.5)
    assert hold.observe(detection, centered=True, now=105.0)


def _centered_detection(artwork_id: str = "mona_lisa") -> ArtworkDetection:
    return ArtworkDetection(
        artwork_id=artwork_id,
        label=artwork_id,
        confidence=0.8,
        center_score=0.8,
        stable=True,
    )


def test_vision_hold_survives_brief_missing_detection():
    hold = VisionHold(hold_seconds=2.0, gap_tolerance_s=0.8)
    detection = _centered_detection()
    assert not hold.observe(detection, centered=True, now=10.0)
    assert not hold.observe(None, centered=False, now=10.4)
    assert not hold.observe(detection, centered=True, now=10.7)
    assert not hold.observe(detection, centered=True, now=11.4)
    assert hold.observe(detection, centered=True, now=12.1)


def test_vision_hold_ignores_brief_wrong_class_flicker():
    hold = VisionHold(hold_seconds=2.0, gap_tolerance_s=0.8)
    mona = _centered_detection("mona_lisa")
    mask = _centered_detection("tutankhamun_mask")
    assert not hold.observe(mona, centered=True, now=20.0)
    assert not hold.observe(mask, centered=True, now=20.3)
    assert not hold.observe(mona, centered=True, now=20.6)
    assert not hold.observe(mona, centered=True, now=21.3)
    assert hold.observe(mona, centered=True, now=22.0)


def test_vision_hold_resets_after_long_gap():
    hold = VisionHold(hold_seconds=2.0, gap_tolerance_s=0.8)
    detection = _centered_detection()
    assert not hold.observe(detection, centered=True, now=30.0)
    assert not hold.observe(None, centered=False, now=30.9)
    assert not hold.observe(detection, centered=True, now=31.0)
    assert not hold.observe(detection, centered=True, now=31.7)
    assert not hold.observe(detection, centered=True, now=32.4)
    assert hold.observe(detection, centered=True, now=33.1)


def test_device_runtime_starts_and_stops_integrated_dashboard():
    container = Container(
        Settings(
            dashboard=DashboardSettings(
                enabled=True,
                host="127.0.0.1",
                port=0,
            )
        )
    )
    runtime = DeviceRuntime(container)
    try:
        status = runtime._start_dashboard()
        assert status.startswith("ready at http://127.0.0.1:")
        assert runtime._dashboard_server.started
        assert runtime._dashboard_service is not None
    finally:
        runtime._stop_dashboard()
    assert not runtime._dashboard_thread.is_alive()


def test_project_dotenv_is_loaded(tmp_path, monkeypatch):
    monkeypatch.delenv("ATLAS_CAMERA_SOURCE", raising=False)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text("{}\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        "ATLAS_CAMERA_SOURCE=http://camera.local:81/stream\n",
        encoding="utf-8",
    )
    try:
        settings = load_settings(config_dir)
        assert settings.hardware.camera_source.endswith(":81/stream")
    finally:
        os.environ.pop("ATLAS_CAMERA_SOURCE", None)


def test_cloud_speech_environment_overrides(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("ATLAS_STT_PROVIDER", "deepgram")
    monkeypatch.setenv("ATLAS_TTS_PROVIDER", "cartesia")
    monkeypatch.setenv("ATLAS_CLOUD_SPEECH_ENABLED", "true")
    monkeypatch.setenv("ATLAS_CARTESIA_VOICE_ID", "custom-voice")
    settings = load_settings(config_dir)
    assert settings.speech.stt_provider == "deepgram"
    assert settings.speech.tts_provider == "cartesia"
    assert settings.speech.cloud_speech_enabled
    assert settings.speech.cartesia_voice_id == "custom-voice"


def test_dashboard_overrides_are_loaded_before_environment(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text(
        "rag:\n  top_k: 5\nspeech:\n  stt_provider: whisper\n",
        encoding="utf-8",
    )
    (config_dir / "dashboard_overrides.yaml").write_text(
        "rag:\n  top_k: 8\nspeech:\n  stt_provider: deepgram\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ATLAS_STT_PROVIDER", "whisper")

    settings = load_settings(config_dir)

    assert settings.rag.top_k == 8
    assert settings.speech.stt_provider == "whisper"
    assert settings.dashboard.config_override_path == (
        config_dir / "dashboard_overrides.yaml"
    )


def test_yolo_backend_environment_override(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.yaml").write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("ATLAS_YOLO_BACKEND", "pytorch")
    settings = load_settings(config_dir)
    assert settings.hardware.yolo_backend == "pytorch"


def test_yolo_labels_match_content_pack_ids():
    assert normalize_yolo_label("mona_lisa") == "mona_lisa"
    assert normalize_yolo_label("starry_night") == "starry_night"
    assert normalize_yolo_label("mask_of_tutankhamun") == "tutankhamun_mask"
    assert normalize_yolo_label("Tutankhamun Mask") == "tutankhamun_mask"
    assert normalize_yolo_label("Van Gogh Sunflowers") == "sunflowers"
    assert normalize_yolo_label("Liberty Leading the People") == (
        "liberty_leading_the_people"
    )
    assert normalize_yolo_label("Girl Pearl Earring") == (
        "girl_with_a_pearl_earring"
    )
    assert normalize_yolo_label("The Great Wave") == (
        "great_wave_off_kanagawa"
    )


def test_center_score_prioritises_center():
    center = bbox_center_score((0.4, 0.4, 0.6, 0.6))
    corner = bbox_center_score((0.0, 0.0, 0.2, 0.2))
    assert center == 1.0
    assert center > corner


def test_yolo_fallback_requires_a_real_distinct_file(tmp_path):
    fallback = tmp_path / "model.pt"
    fallback.write_bytes(b"placeholder")
    detector = YoloDetector(
        model_path="missing.engine",
        fallback_model_path=str(fallback),
    )
    assert detector._fallback_available()
    detector._active_model_path = str(fallback)
    assert not detector._fallback_available()


def test_shokz_aliases_score_even_when_dongle_is_named_loop():
    requested = "Shokz OpenComm2 UC"
    assert device_name_score("Shokz OpenComm2 UC", requested) > 0
    assert device_name_score("Shokz Loop 110 USB Audio", requested) > 0
    assert device_name_score("NVIDIA HDMI", requested) == 0


def test_sounddevice_input_prefers_pulse_when_shokz_is_default(
    monkeypatch,
):
    fake_sounddevice = SimpleNamespace(
        query_devices=lambda: [
            {"name": "Shokz Loop120 USB Audio", "max_input_channels": 1},
            {"name": "pulse", "max_input_channels": 32},
        ]
    )
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sounddevice)
    monkeypatch.setattr(
        "atlas.audio.devices.find_pulse_defaults",
        lambda: {"source": "alsa_input.usb-Shokz_Loop120-02.mono-fallback"},
    )

    assert find_sounddevice_input("Shokz OpenComm2 UC") == 1


def test_sounddevice_input_uses_raw_device_when_pulse_source_is_unknown(monkeypatch):
    fake_sounddevice = SimpleNamespace(
        query_devices=lambda: [
            {"name": "Shokz Loop120 USB Audio", "max_input_channels": 1},
            {"name": "NVIDIA HDMI", "max_input_channels": 0},
            {"name": "pulse", "max_input_channels": 32},
        ]
    )
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sounddevice)
    monkeypatch.setattr(
        "atlas.audio.devices.find_pulse_defaults",
        lambda: {},
    )
    monkeypatch.setattr(
        "atlas.audio.devices.configure_pulse_capture",
        lambda _requested: None,
    )
    assert find_sounddevice_input("Shokz OpenComm2 UC") == 0


def test_sounddevice_input_pins_named_pulse_source(monkeypatch):
    fake_sounddevice = SimpleNamespace(
        query_devices=lambda: [
            {"name": "Shokz Loop120 USB Audio", "max_input_channels": 1},
            {"name": "pulse", "max_input_channels": 32},
        ]
    )
    monkeypatch.setitem(sys.modules, "sounddevice", fake_sounddevice)
    monkeypatch.setattr(
        "atlas.audio.devices.find_pulse_defaults",
        lambda: {"source": "alsa_input.platform-sound.analog-stereo"},
    )
    monkeypatch.setattr(
        "atlas.audio.devices.configure_pulse_capture",
        lambda _requested: "alsa_input.usb-Shokz_Loop120.mono-fallback",
    )
    assert find_sounddevice_input("Shokz OpenComm2 UC") == 1


def test_configure_pulse_capture_exports_named_source(monkeypatch):
    calls = []
    monkeypatch.delenv("PULSE_SOURCE", raising=False)
    monkeypatch.setattr(
        "atlas.audio.devices.find_pulse_capture",
        lambda _requested: "alsa_input.usb-Shokz_Loop120.mono-fallback",
    )
    monkeypatch.setattr(
        "atlas.audio.devices.subprocess.run",
        lambda args, **_kwargs: calls.append(args) or SimpleNamespace(returncode=0),
    )

    source = configure_pulse_capture("Shokz OpenComm2 UC")

    assert source == "alsa_input.usb-Shokz_Loop120.mono-fallback"
    assert os.environ["PULSE_SOURCE"] == source
    assert calls == [["pactl", "set-default-source", source]]


def test_pactl_defaults_are_parsed_for_shokz_fallback():
    output = """\
Server Name: pulseaudio
Default Sink: alsa_output.usb-Shokz_Loop120-02.analog-stereo
Default Source: alsa_input.usb-Shokz_Loop120-02.mono-fallback
"""
    assert parse_pactl_defaults(output) == {
        "sink": "alsa_output.usb-Shokz_Loop120-02.analog-stereo",
        "source": "alsa_input.usb-Shokz_Loop120-02.mono-fallback",
    }


def test_find_pulse_defaults_reads_pactl_info(monkeypatch):
    output = """\
Default Sink: alsa_output.usb-Shokz_Loop120-02.analog-stereo
Default Source: alsa_input.usb-Shokz_Loop120-02.mono-fallback
"""
    monkeypatch.setattr(
        "atlas.audio.devices.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=output),
    )

    assert find_pulse_defaults() == {
        "sink": "alsa_output.usb-Shokz_Loop120-02.analog-stereo",
        "source": "alsa_input.usb-Shokz_Loop120-02.mono-fallback",
    }


def test_named_shokz_pulse_device_is_selected_without_being_default():
    output = """\
0\talsa_output.platform-sound.analog-stereo\tmodule-alsa-card.c
1\talsa_output.usb-Shokz_Loop120-02.analog-stereo\tmodule-alsa-card.c
"""
    assert select_pulse_device(output, "Shokz OpenComm2 UC") == (
        "alsa_output.usb-Shokz_Loop120-02.analog-stereo"
    )


def test_capture_selection_ignores_playback_monitor():
    output = """\
1\talsa_output.usb-Shokz_Loop120-02.analog-stereo.monitor\tmodule-alsa-card.c
2\talsa_input.usb-Shokz_Loop120-02.mono-fallback\tmodule-alsa-card.c
"""
    assert select_pulse_device(
        output, "Shokz OpenComm2 UC", include_monitors=False
    ) == "alsa_input.usb-Shokz_Loop120-02.mono-fallback"


def test_rag_preloads_on_runtime_thread():
    class ReadyComponent:
        def warm_up(self):
            return None

    class WarmEmbedder:
        def __init__(self):
            self.thread = None

        def embed_one(self, _text):
            self.thread = threading.get_ident()
            return [0.0]

    class ReadyCamera:
        def start(self, timeout_s):
            assert timeout_s == 10.0

    class FakeContainer:
        def __init__(self):
            self.camera_source = ReadyCamera()
            self.vision_detector = ReadyComponent()
            self.stt = ReadyComponent()
            self.tts = ReadyComponent()
            self.embedder = WarmEmbedder()
            self.settings = SimpleNamespace(
                hardware=SimpleNamespace(enable_ev3=False)
            )
            self.retriever_thread = None

        @property
        def retriever(self):
            self.retriever_thread = threading.get_ident()
            return object()

    container = FakeContainer()
    runtime_thread = threading.get_ident()
    statuses = DeviceRuntime(container).preload()
    assert statuses["RAG"] == "ready"
    assert container.embedder.thread == runtime_thread
    assert container.retriever_thread == runtime_thread


def test_device_runtime_keeps_running_while_camera_recovers():
    class ReadyComponent:
        def warm_up(self):
            return None

    class WarmEmbedder:
        def embed_one(self, _text):
            return [0.0]

    class RecoveringCamera:
        def start(self, timeout_s):
            assert timeout_s == 10.0
            raise RuntimeError("camera did not become ready: Wi-Fi unavailable")

    class FakeContainer:
        def __init__(self):
            self.camera_source = RecoveringCamera()
            self.vision_detector = ReadyComponent()
            self.stt = ReadyComponent()
            self.tts = ReadyComponent()
            self.embedder = WarmEmbedder()
            self.settings = SimpleNamespace(
                hardware=SimpleNamespace(enable_ev3=False)
            )

        @property
        def retriever(self):
            return object()

    runtime = DeviceRuntime(FakeContainer())
    statuses = runtime.preload()

    assert statuses["Camera"].startswith("recovering:")
    assert "Camera" not in runtime._required_components()
    assert runtime._required_components() == ("YOLO", "STT", "TTS", "RAG")


class RecordingEV3(EV3Hardware):
    def __init__(self):
        super().__init__("00:00:00:00:00:00")
        self.commands: list[str] = []

    def _send_text(self, command: str, **_kwargs) -> bool:
        self.commands.append(command)
        return True


def test_ev3_artwork_slot_mapping_matches_physical_ports():
    ev3 = RecordingEV3()
    ev3.focus_artwork("starry_night")
    ev3.focus_artwork("mona_lisa")
    ev3.focus_artwork("tutankhamun_mask")
    ev3.reset_exhibit()
    assert ev3.commands == [
        "raise:slot_1",
        "raise:slot_2",
        "raise:slot_3",
        "raise_all",
    ]


def _mailbox_packet(name: str, value: str) -> bytes:
    name_bytes = (name + "\0").encode()
    payload = (value + "\0").encode()
    size = 7 + len(name_bytes) + len(payload)
    return struct.pack(
        f"<HHBBB{len(name_bytes)}sH{len(payload)}s",
        size,
        1,
        0x81,
        0x9E,
        len(name_bytes),
        name_bytes,
        len(payload),
        payload,
    )


def test_ev3_mailbox_framing_round_trip():
    class FakeSocket:
        def __init__(self, response: bytes):
            self.response = bytearray(response)
            self.sent = b""

        def sendall(self, data: bytes) -> None:
            self.sent += data

        def recv(self, size: int) -> bytes:
            data = bytes(self.response[:size])
            del self.response[:size]
            return data

    client = _MailboxClient.__new__(_MailboxClient)
    client.socket = FakeSocket(_mailbox_packet("atlas", "pong"))
    assert client.exchange("atlas", "ping") == "pong"
    assert client.socket.sent == _mailbox_packet("atlas", "ping")
