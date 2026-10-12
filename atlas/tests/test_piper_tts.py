"""Regression tests for Piper language voice selection."""

from __future__ import annotations

import subprocess
import wave
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
        "atlas.audio.piper_tts.subprocess.Popen",
        lambda command, **_kwargs: (
            played.append(command)
            or SimpleNamespace(
                returncode=0, communicate=lambda **_kw: (b"", b""),
            )
        ),
    )

    assert tts._play_wav(str(output_path)) is True
    assert sorted(played) == sorted(
        [
            ["paplay", "--device=pulse-Shokz", str(output_path)],
            ["paplay", "--device=pulse-Judge speaker", str(output_path)],
        ]
    )


def test_piper_long_answer_is_not_cut_off_at_thirty_seconds(monkeypatch, tmp_path):
    output_path = tmp_path / "long-synthetic-answer.wav"
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(10)
        wav_file.writeframes(b"\x00\x00" * 600)  # 60 s without real playback.
    deadlines = []
    player = SimpleNamespace(returncode=0, killed=False)

    def communicate(*, timeout, **_kwargs):
        deadlines.append(timeout)
        if not player.killed and timeout < 60:
            raise subprocess.TimeoutExpired("synthetic audio", timeout)
        return b"", b""

    def kill():
        player.killed = True
        player.returncode = -9

    player.communicate = communicate
    player.kill = kill
    monkeypatch.setattr(
        "atlas.audio.piper_tts.subprocess.Popen", lambda *_a, **_k: player,
    )
    monkeypatch.setattr("atlas.audio.piper_tts.find_pulse_playback", lambda _n: None)
    monkeypatch.setattr("atlas.audio.piper_tts.find_alsa_playback", lambda _n: "mock")
    tts = PiperTTS("mock-en", "mock-fr")
    assert tts._play_wav(str(output_path)) is True
    assert not player.killed
    assert deadlines == [70.0]
