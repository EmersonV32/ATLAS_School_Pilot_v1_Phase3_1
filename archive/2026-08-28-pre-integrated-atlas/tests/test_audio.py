"""Tests for audio module."""
import pytest
from atlas.audio.stt import TranscriptResult
from atlas.audio.mock_stt import MockSTT
from atlas.audio.mock_tts import MockTTS


def test_mock_stt_returns_transcript():
    stt = MockSTT()
    result = stt.listen()
    assert isinstance(result, TranscriptResult)
    assert result.text
    assert result.language in ("en", "fr")
    assert result.age_hint in ("child", "teen", "adult")


def test_mock_stt_cycles_questions():
    stt = MockSTT()
    texts = [stt.listen().text for _ in range(10)]
    # Should see repetition after 5 (canned list has 5 items)
    assert texts[0] == texts[5]


def test_mock_stt_covers_both_languages():
    stt = MockSTT()
    langs = {stt.listen().language for _ in range(5)}
    assert "en" in langs
    assert "fr" in langs


def test_mock_tts_prints_output(capsys):
    tts = MockTTS()
    tts.speak("Hello museum visitor", language="en")
    captured = capsys.readouterr()
    assert "Hello museum visitor" in captured.out
    assert "EN" in captured.out


def test_mock_tts_french(capsys):
    tts = MockTTS()
    tts.speak("Bienvenue au musee", language="fr")
    captured = capsys.readouterr()
    assert "Bienvenue au musee" in captured.out
    assert "FR" in captured.out
