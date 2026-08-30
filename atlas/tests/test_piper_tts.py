"""Regression tests for Piper language voice selection."""

from __future__ import annotations

from pathlib import Path

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
