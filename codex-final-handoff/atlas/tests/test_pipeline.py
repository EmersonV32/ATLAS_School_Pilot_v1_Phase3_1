"""Tests for SessionRunner pipeline."""

import logging

import pytest

from atlas.audio.mock_stt import MockSTT
from atlas.audio.mock_tts import MockTTS
from atlas.audio.stt import TranscriptResult
from atlas.dialogue.dialogue_engine import DialogueEngine, DialogueResult
from atlas.dialogue.mock_llm_client import MockLLMClient
from atlas.hardware.mock_hardware import MockHardware
from atlas.pipeline.session_runner import (
    SessionResult,
    SessionRunner,
    requested_language,
)
from atlas.vision.detector import ArtworkDetection
from atlas.vision.mock_detector import MockDetector


def _mock_retriever(artwork_id: str, query: str) -> list[dict]:
    return [
        {"text": f"This is a famous artwork: {artwork_id.replace('_', ' ')}."},
        {
            "text": (
                f"Visitors often ask: {query!r}. "
                "The work has great historical significance."
            )
        },
    ]


def _make_runner(**kwargs) -> SessionRunner:
    engine = DialogueEngine(llm_client=MockLLMClient())
    _unused = ()
    defaults = dict(
        detector=MockDetector(),
        stt=MockSTT(),
        tts=MockTTS(),
        hardware=MockHardware(),
        dialogue_engine=engine,
        retriever=_mock_retriever,
    )
    defaults.update(kwargs)
    return SessionRunner(**defaults)


def test_single_cycle_succeeds():
    runner = _make_runner()
    result = runner.run_once(frame=None)
    assert isinstance(result, SessionResult)
    assert result.success
    assert result.error is None


def test_result_has_all_fields():
    runner = _make_runner()
    result = runner.run_once(frame=None)
    assert result.detection is not None
    assert result.transcript is not None
    assert result.dialogue is not None
    assert result.dialogue.response


def test_five_consecutive_cycles():
    runner = _make_runner()
    results = [runner.run_once(None) for _ in range(5)]
    assert all(r.success for r in results)


def test_testing_mode_logs_question_answer_and_stage_timings(caplog):
    caplog.set_level(logging.INFO, logger="atlas.pipeline.session_runner")
    runner = _make_runner(log_transcripts=True, log_llm_responses=True)
    result = runner.run_once(frame=None)

    assert result.success
    assert f"[STT final] {result.transcript.text}" in caplog.text
    assert f"[LLM final] {result.dialogue.response}" in caplog.text
    assert "[Timing] STT total" in caplog.text
    assert "[Timing] RAG" in caplog.text
    assert "[Timing] LLM first sentence" in caplog.text
    assert "[Timing] Cycle total" in caplog.text


def test_default_mode_does_not_log_conversation_text(caplog):
    caplog.set_level(logging.INFO, logger="atlas.pipeline.session_runner")
    result = _make_runner().run_once(frame=None)

    assert result.success
    assert result.transcript.text not in caplog.text
    assert result.dialogue.response not in caplog.text


def test_no_detection_returns_error():
    from atlas.vision.mock_detector import MockDetector

    # always_detect=False: first call returns None
    runner = _make_runner(detector=MockDetector(always_detect=False))
    result = runner.run_once(None)
    assert not result.success
    assert result.error == "no_detection"


def test_hardware_called_on_success(capsys):
    runner = _make_runner()
    runner.run_once(None)
    captured = capsys.readouterr()
    assert "[HW] Focus artwork" in captured.out
    assert "[HW] All artworks up" in captured.out


def test_tts_called_on_success(capsys):
    runner = _make_runner()
    runner.run_once(None)
    captured = capsys.readouterr()
    assert "[TTS:CUE]" in captured.out
    assert "[TTS:" in captured.out


def test_stt_is_prepared_before_listening_cue():
    events = []

    class OrderedSTT(MockSTT):
        def prepare_listen(self):
            events.append("prepare")

        def listen(self, duration_s=5.0):
            events.append("listen")
            return super().listen(duration_s)

    class OrderedTTS(MockTTS):
        def cue(self):
            events.append("cue")
            return True

    runner = _make_runner(stt=OrderedSTT(), tts=OrderedTTS())
    assert runner.run_once(None).success
    assert events[:3] == ["prepare", "cue", "listen"]


def test_preferred_language_is_applied_to_stt_and_transcript():
    class LanguageSTT(MockSTT):
        def __init__(self):
            super().__init__()
            self.language = None

        def set_language(self, language):
            self.language = language

        def listen(self, duration_s=5.0):
            return TranscriptResult("Qui a peint la Joconde?", "en")

    stt = LanguageSTT()
    runner = _make_runner(stt=stt)
    runner.set_preferred_language("fr")
    result = runner.run_once(None)

    assert result.success
    assert stt.language == "fr"
    assert result.transcript.language == "fr"


def test_preferred_profile_is_forwarded_to_dialogue_engine():
    class RecordingEngine:
        def __init__(self):
            self.profile = None

        def respond(self, **kwargs):
            self.profile = kwargs["profile"]
            return DialogueResult(
                response="A verified response.",
                language=kwargs["language"],
                grounded=True,
                grounding_reason="test",
                filtered=False,
            )

    engine = RecordingEngine()
    runner = _make_runner(dialogue_engine=engine)
    runner.set_preferred_profile("teen")
    result = runner.respond_to_transcript(
        TranscriptResult("Tell me more", "en"),
        detection=ArtworkDetection(
            artwork_id="mona_lisa",
            label="Mona Lisa",
            confidence=1.0,
            source="test",
        ),
    )

    assert result.success
    assert runner.preferred_profile == "teen"
    assert engine.profile == "teen"

    runner.set_preferred_profile("not-a-profile")
    assert runner.preferred_profile == "adult_beginner"


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("Switch back to English", "en"),
        ("Peux-tu me parler en anglais?", "en"),
        ("Parle-moi en francais", "fr"),
        ("Puedes hablar espanol", "es"),
        ("Puoi parlare italiano", "it"),
    ],
)
def test_spoken_language_commands_are_detected(command, expected):
    assert requested_language(command) == expected


def test_artwork_language_question_is_not_a_switch_command():
    assert requested_language("Who spoke English at court?") is None


def test_language_switch_is_local_and_skips_rag_and_llm():
    tts = MockTTS()

    def should_not_retrieve(*_args):
        pytest.fail("language switches must not call RAG")

    runner = _make_runner(tts=tts, retriever=should_not_retrieve)
    result = runner.respond_to_transcript(
        TranscriptResult("Peux-tu me parler en anglais?", "fr")
    )

    assert result.success
    assert result.event == "language_changed"
    assert result.transcript.language == "en"
    assert result.dialogue.language == "en"
    assert result.dialogue.grounding_reason == "local_language_switch"
    assert runner.preferred_language == "en"


def test_voice_capture_command_corrects_detection_then_listens_again():
    class SequenceSTT:
        def __init__(self):
            self.results = [
                TranscriptResult("Capture cette œuvre", "fr", "adult"),
                TranscriptResult("Qui l'a peinte?", "fr", "adult"),
            ]

        def listen(self, duration_s=5.0):
            return self.results.pop(0)

    class FakeManualCapture:
        def identify(self, frame):
            return ArtworkDetection(
                artwork_id="starry_night",
                label="The Starry Night",
                confidence=1.0,
                source="manual_capture",
                stable=True,
            )

    stt = SequenceSTT()
    runner = _make_runner(stt=stt, manual_capture=FakeManualCapture())
    result = runner.run_once(frame=object())
    assert result.success
    assert result.detection.artwork_id == "starry_night"
    assert result.transcript.text == "Qui l'a peinte?"
    assert not stt.results


def test_make_retriever_adapter():
    """Verify make_retriever wraps a mock retriever correctly."""
    from atlas.pipeline.session_runner import make_retriever

    class FakeContextPack:
        def __init__(self):
            from types import SimpleNamespace

            self.chunks = [
                SimpleNamespace(text="chunk one", chunk_id="c1"),
                SimpleNamespace(text="chunk two", chunk_id="c2"),
            ]

    class FakeRetriever:
        def retrieve(self, query, filters=None):
            return FakeContextPack()

    fn = make_retriever(FakeRetriever())
    result = fn("starry_night", "Who painted this?")
    assert len(result) == 2
    assert result[0]["text"] == "chunk one"
    assert result[0]["chunk_id"] == "c1"


def test_make_retriever_does_not_guess_an_artwork_for_a_deictic_question():
    """A collection search must not make 'it' refer to an arbitrary artwork."""
    from atlas.pipeline.session_runner import make_retriever

    class FakeRetriever:
        def retrieve(self, query, filters=None):
            pytest.fail("ambiguous questions without vision context must not retrieve")

    assert make_retriever(FakeRetriever())(None, "Who created it?") == []


def test_continuous_question_without_artwork_searches_full_collection():
    calls = []

    def retriever(artwork_id, query, language="en"):
        calls.append((artwork_id, query, language))
        return [{"text": "The collection contains several famous artworks."}]

    runner = _make_runner(retriever=retriever)
    result = runner.respond_to_transcript(
        TranscriptResult("Which painting has stars?", "en")
    )

    assert result.success
    assert result.detection is None
    assert calls == [(None, "Which painting has stars?", "en")]


def test_listen_once_can_skip_repeated_cue():
    events = []

    class RecordingSTT(MockSTT):
        def prepare_listen(self):
            events.append("prepare")

        def listen(self, duration_s=5.0):
            events.append("listen")
            return super().listen(duration_s)

    class RecordingTTS(MockTTS):
        def cue(self):
            events.append("cue")
            return True

    runner = _make_runner(stt=RecordingSTT(), tts=RecordingTTS())
    assert runner.listen_once(play_cue=False) is not None
    assert events == ["prepare", "listen"]
