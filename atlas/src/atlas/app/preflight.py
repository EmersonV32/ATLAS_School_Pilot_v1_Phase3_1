"""Read-only ATLAS device preflight for the Jetson."""

from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path

from atlas.app.dependency_container import build_container
from atlas.audio.devices import (
    audio_device_snapshot,
    device_name_score,
    find_alsa_playback,
    find_pulse_capture,
    find_pulse_defaults,
    find_pulse_playback,
)
from atlas.models.enums import RunMode


def _line(ok: bool, name: str, detail: str) -> None:
    print(f"[{'OK' if ok else 'FAIL'}] {name}: {detail}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ATLAS Jetson hardware preflight")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--open-camera", action="store_true")
    args = parser.parse_args()

    container = build_container(args.config_dir)
    container.settings.mode = RunMode.DEVICE
    hw = container.settings.hardware
    speech = container.settings.speech
    llm = container.settings.llm
    failures = 0

    required_modules = ["cv2", "torch", "ultralytics", "faster_whisper", "piper"]
    if speech.cloud_speech_enabled and (
        speech.stt_provider == "deepgram" or speech.tts_provider == "cartesia"
    ):
        required_modules.append("websockets")
    if speech.cloud_speech_enabled and speech.stt_provider == "deepgram":
        required_modules.append("onnxruntime")
    if llm.cloud_llm_enabled and llm.provider == "gemini":
        required_modules.append("google.genai")
    if llm.cloud_llm_enabled and llm.provider in {"openai", "kimi"}:
        required_modules.append("openai")

    for module in required_modules:
        try:
            importlib.import_module(module)
            _line(True, module, "imported")
        except Exception as exc:
            failures += 1
            _line(False, module, str(exc))

    try:
        import torch  # type: ignore

        cuda = bool(torch.cuda.is_available())
        _line(cuda, "CUDA", torch.cuda.get_device_name(0) if cuda else "unavailable")
        failures += int(not cuda)
    except Exception as exc:
        failures += 1
        _line(False, "CUDA", str(exc))

    engine_path = Path(hw.yolo_tensorrt_path).expanduser()
    prefer_engine = hw.yolo_backend == "tensorrt" or (
        hw.yolo_backend == "auto" and engine_path.is_file()
    )
    assets = {
        "YOLO active model": (
            engine_path if prefer_engine else Path(hw.yolo_model_path).expanduser()
        ),
        "English voice": Path(hw.piper_voice_en).expanduser(),
        "French voice": Path(hw.piper_voice_fr).expanduser(),
    }
    optional_voices = {
        "Spanish voice": hw.piper_voice_es,
        "Italian voice": hw.piper_voice_it,
        "Traditional Chinese voice": hw.piper_voice_zh,
    }
    assets.update(
        {
            name: Path(path).expanduser()
            for name, path in optional_voices.items()
            if path.strip()
        }
    )
    for name, path in assets.items():
        exists = path.is_file()
        failures += int(not exists)
        _line(exists, name, str(path))

    if speech.cloud_speech_enabled and speech.stt_provider == "deepgram":
        silero_path = Path(speech.silero_model_path).expanduser()
        silero_ok = silero_path.is_file()
        failures += int(not silero_ok)
        _line(silero_ok, "Silero ONNX model", str(silero_path))

    devices = audio_device_snapshot()
    matches = [
        str(device.get("name", ""))
        for device in devices
        if device_name_score(str(device.get("name", "")), hw.headset_name)
    ]
    pulse_defaults = find_pulse_defaults()
    pulse_matches = [
        f"PulseAudio {kind}={name}"
        for kind, name in pulse_defaults.items()
        if device_name_score(name, hw.headset_name)
    ]
    output_name = hw.audio_output_name or hw.headset_name
    pulse_sink = find_pulse_playback(output_name)
    pulse_source = find_pulse_capture(hw.headset_name)
    if pulse_sink and not any(pulse_sink in match for match in pulse_matches):
        pulse_matches.append(f"PulseAudio sink={pulse_sink}")
    if pulse_source and not any(pulse_source in match for match in pulse_matches):
        pulse_matches.append(f"PulseAudio source={pulse_source}")
    matches.extend(pulse_matches)
    playback_device = find_alsa_playback(output_name)
    if playback_device:
        matches.append(f"ALSA playback={playback_device}")
    audio_ok = bool(pulse_sink) and bool(pulse_source) and bool(playback_device)
    failures += int(not audio_ok)
    _line(
        audio_ok,
        "Split audio route",
        f"input={hw.headset_name}; output={output_name}; "
        + (", ".join(matches) if matches else "not connected"),
    )

    if hw.enable_ev3:
        bluetooth_ok = all(
            hasattr(__import__("socket"), name)
            for name in ("AF_BLUETOOTH", "BTPROTO_RFCOMM")
        )
        failures += int(not bluetooth_ok)
        _line(
            bluetooth_ok,
            "Bluetooth RFCOMM",
            "supported" if bluetooth_ok else "not supported by this Python build",
        )
        address_ok = bool(hw.ev3_bt_address)
        failures += int(not address_ok)
        _line(address_ok, "EV3 address", hw.ev3_bt_address or "not configured")
    else:
        _line(True, "EV3", "disabled until the brick is present")

    llm_envs = {
        "gemini": ("Gemini key", llm.gemini_api_key_env),
        "openai": ("OpenAI key", llm.openai_api_key_env),
        "kimi": ("Kimi key", llm.kimi_api_key_env),
    }
    if llm.cloud_llm_enabled and llm.provider in llm_envs:
        name, env_name = llm_envs[llm.provider]
        key_ok = bool(os.getenv(env_name))
        failures += int(not key_ok)
        _line(key_ok, name, "set" if key_ok else f"missing ({env_name})")
    else:
        _line(True, "LLM", "mock/cloud-disabled")

    if speech.cloud_speech_enabled:
        cloud_speech_keys = []
        if speech.stt_provider == "deepgram":
            cloud_speech_keys.append(("Deepgram key", speech.deepgram_api_key_env))
        if speech.tts_provider == "cartesia":
            cloud_speech_keys.append(("Cartesia key", speech.cartesia_api_key_env))
        for name, env_name in cloud_speech_keys:
            key_ok = bool(os.getenv(env_name))
            failures += int(not key_ok)
            _line(key_ok, name, "set" if key_ok else f"missing ({env_name})")
    else:
        _line(True, "Cloud speech", "disabled")

    if args.open_camera:
        try:
            container.camera_source.start(timeout_s=10)
            status = container.camera_source.status()
            _line(True, "Camera", f"source={status['source']!r}, fresh frame received")
        except Exception as exc:
            failures += 1
            _line(False, "Camera", str(exc))
        finally:
            container.close()
    else:
        _line(True, "Camera", f"configured source={hw.camera_source!r} (not opened)")

    print(f"\nPreflight result: {failures} failure(s)")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
