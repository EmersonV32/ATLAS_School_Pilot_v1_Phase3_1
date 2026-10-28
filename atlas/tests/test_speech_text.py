"""French pronunciation is normalized at the speech-provider boundaries."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from atlas.audio.cartesia_tts import CartesiaTTS, build_cartesia_request
from atlas.audio.fallback import FallbackTTS
from atlas.audio.piper_tts import PiperTTS
from atlas.audio.speech_text import french_number_words, normalize_speech_text


@pytest.mark.parametrize(
    ("number", "words"),
    [
        (0, "zéro"),
        (17, "dix-sept"),
        (21, "vingt et un"),
        (71, "soixante et onze"),
        (80, "quatre-vingts"),
        (81, "quatre-vingt-un"),
        (96, "quatre-vingt-seize"),
        (100, "cent"),
        (180, "cent quatre-vingts"),
        (200, "deux cents"),
        (201, "deux cent un"),
        (1000, "mille"),
        (1503, "mille cinq cent trois"),
        (1665, "mille six cent soixante-cinq"),
        (1789, "mille sept cent quatre-vingt-neuf"),
        (1830, "mille huit cent trente"),
        (1889, "mille huit cent quatre-vingt-neuf"),
        (1896, "mille huit cent quatre-vingt-seize"),
        (1900, "mille neuf cents"),
        (2000, "deux mille"),
        (2026, "deux mille vingt-six"),
    ],
)
def test_french_number_forms(number, words):
    assert french_number_words(number) == words


@pytest.mark.parametrize("number", [-1, 10000])
def test_french_number_expansion_rejects_unsupported_values(number):
    with pytest.raises(ValueError):
        french_number_words(number)


@pytest.mark.parametrize("language", ["fr", "fr-CA", "fr-FR", "FR-ca"])
def test_french_dates_and_year_ranges_are_full_words(language):
    original = "Créée en 1896. Vers 1830–1832, le 14 juillet 1789."
    spoken = normalize_speech_text(original, language)

    assert spoken == (
        "Créée en mille huit cent quatre-vingt-seize. "
        "Vers mille huit cent trente à mille huit cent trente-deux, "
        "le quatorze juillet mille sept cent quatre-vingt-neuf."
    )
    assert original == "Créée en 1896. Vers 1830–1832, le 14 juillet 1789."
    assert normalize_speech_text(spoken, language) == spoken


def test_spaced_year_is_expanded_only_after_a_french_date_cue():
    assert normalize_speech_text("Peinte en 1 8 9 6.", "fr") == (
        "Peinte en mille huit cent quatre-vingt-seize."
    )


@pytest.mark.parametrize("year", ["1 896", "1\u00a0896", "1\u202f896"])
def test_french_grouped_year_remains_one_spoken_number(year):
    assert normalize_speech_text("Peinte en " + year + ".", "fr") == (
        "Peinte en mille huit cent quatre-vingt-seize."
    )


@pytest.mark.parametrize("written", ["14/07/1789", "14.07.1789", "1789-07-14"])
def test_numeric_calendar_dates_are_validated_and_spoken_in_french(written):
    assert normalize_speech_text(written, "fr") == (
        "quatorze juillet mille sept cent quatre-vingt-neuf"
    )


@pytest.mark.parametrize("written", ["1 janvier 2000", "1er janvier 2000"])
def test_first_day_of_month_uses_premier(written):
    assert normalize_speech_text(written, "fr") == "premier janvier deux mille"


def test_invalid_calendar_date_is_not_reinterpreted():
    assert normalize_speech_text("31/02/1896", "fr") == "31/02/1896"


@pytest.mark.parametrize("language", ["en", "es", "it", "zh-Hant", "de"])
def test_other_languages_remain_unchanged(language):
    original = "1896, 1830–1832, 14 July 1789."
    assert normalize_speech_text(original, language) == original


@pytest.mark.parametrize(
    "technical_text",
    [
        "https://museum.example/1896?item=1830",
        "www.museum.example/1896",
        "item1896@example.org",
        "INV-1896",
        "B1896",
        "atlas/1896",
        "1896.5",
        "1896,5",
        "12345",
        "1 896 000",
        "`1896`",
    ],
)
def test_technical_tokens_decimals_and_large_numbers_are_preserved(technical_text):
    assert normalize_speech_text(technical_text, "fr") == technical_text


def test_cartesia_request_expands_french_without_changing_original_answer():
    original = "Le tableau date de 1896."
    request = build_cartesia_request(
        text=original,
        language="fr-CA",
        model="sonic-3.5",
        voice_id="voice-id",
        sample_rate=24000,
        context_id="test-context",
    )

    assert request["transcript"] == (
        "Le tableau date de mille huit cent quatre-vingt-seize."
    )
    assert request["language"] == "fr"
    assert original == "Le tableau date de 1896."


def test_french_dates_preserve_cartesia_brand_pronunciation_and_other_acronyms():
    request = build_cartesia_request(
        text="ATLAS parle de 1896 et de la NASA.",
        language="fr-CA", model="sonic-3.5", voice_id="voice-id",
        sample_rate=24000, context_id="test-context",
    )
    assert request["transcript"] == (
        "Atlas parle de mille huit cent quatre-vingt-seize et de la NASA."
    )


def test_cartesia_continuous_segments_expand_using_utterance_language(monkeypatch):
    requests = []

    class Connection:
        def send(self, raw):
            requests.append(json.loads(raw))

    tts = CartesiaTTS(voice_id="voice-id")
    tts._connection = Connection()
    # Suppress only the receiving worker; the real segment request path runs.
    monkeypatch.setattr(
        "atlas.audio.cartesia_tts.threading.Thread.start", lambda _: None
    )

    assert tts.begin_utterance("fr-CA")
    assert tts.speak_segment("Créée en 1896.", "en")
    assert requests[0]["transcript"] == (
        "Créée en mille huit cent quatre-vingt-seize. "
    )
    assert requests[0]["continue"] is True


@pytest.mark.parametrize("private", [False, True])
def test_piper_synthesis_input_expands_french_dates(monkeypatch, private):
    tts = PiperTTS(voice_en="english.onnx", voice_fr="french.onnx")
    tts._command = ["piper"]
    captured = []

    def synthesize(command, **kwargs):
        captured.append(kwargs["input_data"].decode("utf-8"))
        Path(command[-1]).write_bytes(b"fake wave")
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(tts, "_run_process", synthesize)
    monkeypatch.setattr(tts, "_play_wav", lambda _, **_kwargs: True)
    speak = tts.speak_private_local if private else tts.speak

    assert speak("Créée en 1896.", "fr-CA")
    assert captured == ["Créée en mille huit cent quatre-vingt-seize.\n"]


def test_french_date_stays_normalized_after_cloud_failure(monkeypatch):
    cloud = CartesiaTTS(voice_id="voice-id")
    local = PiperTTS(voice_en="english.onnx", voice_fr="french.onnx")
    local._command = ["piper"]
    captured = []

    def synthesize(command, **kwargs):
        captured.append(kwargs["input_data"].decode("utf-8"))
        Path(command[-1]).write_bytes(b"fake wave")
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(cloud, "speak", lambda *_args: False)
    monkeypatch.setattr(local, "_run_process", synthesize)
    monkeypatch.setattr(local, "_play_wav", lambda _, **_kwargs: True)
    tts = FallbackTTS(cloud, local)
    tts.primary_ready = tts.fallback_ready = True

    assert tts.speak("Peinte en 1896.", "fr-CA")
    assert tts.last_provider == "PiperTTS"
    assert captured == ["Peinte en mille huit cent quatre-vingt-seize.\n"]
