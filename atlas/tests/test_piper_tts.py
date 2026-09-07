"""Regression tests for Piper language voice selection."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from atlas.audio.piper_tts import PiperTTS


def test_piper_uses_configured_chinese_voice_for_traditional_chinese():
    tts = PiperTTS(
        voice_en="english.onnx",
        voice_fr="french.onnx",
        voice_zh="chinese.onnx",
    )

    assert tts._voice_for("zh-Hant") == Path("chinese.onnx")


def test_piper_uses_english_only_when_a_language_voice_is_not_configured():
    tts = PiperTTS(voice_en="english.onnx", voice_fr="french.onnx")

    assert tts._voice_for("zh") == Path("english.onnx")


def test_piper_wav_playback_fans_out_to_both_outputs(monkeypatch, tmp_path):
    output_path = tmp_path / "speech.wav"
    output_path.write_bytes(b"placeholder")
    played = []
    tts = PiperTTS(
        voice_en="english.onnx",
        voice_fr="french.onnx",
        output_device_name="Shokz|||Judge speaker",
    )
    monkeypatch.setattr(
        "atlas.audio.piper_tts.find_pulse_playback",
        lambda name: f"pulse-{name}",
    )
    monkeypatch.setattr("atlas.audio.piper_tts.shutil.which", lambda _name: True)
    monkeypatch.setattr(
        "atlas.audio.piper_tts.subprocess.run",
        lambda command, **_kwargs: (
            played.append(command)
            or SimpleNamespace(returncode=0, stderr=b"")
        ),
    )

    assert tts._play_wav(str(output_path)) is True
    assert sorted(played) == sorted(
        [
            ["paplay", "--device=pulse-Shokz", str(output_path)],
            ["paplay", "--device=pulse-Judge speaker", str(output_path)],
        ]
    )
