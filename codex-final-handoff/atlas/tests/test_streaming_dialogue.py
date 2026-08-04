"""Tests for concurrent sentence-level LLM to TTS streaming."""

from __future__ import annotations

import threading

from atlas.dialogue.dialogue_engine import DialogueEngine
from atlas.dialogue.sentence_stream import SentenceAssembler

CONTEXT = [
    {
        "text": (
            "Leonardo da Vinci painted the Mona Lisa. The painting is displayed "
            "at the Louvre Museum in Paris."
        )
    }
]


def test_sentence_assembler_keeps_partial_tokens():
    assembler = SentenceAssembler()
    assert assembler.feed("Leonardo painted the Mona") == []
    assert assembler.feed(" Lisa. It hangs ") == ["Leonardo painted the Mona Lisa."]
    assert assembler.feed("at the Louvre!") == ["It hangs at the Louvre!"]
    assert assembler.flush() == ""


def test_llm_generation_continues_while_first_sentence_is_spoken():
    second_generated = threading.Event()

    class StreamingLLM:
        def generate_stream(self, _messages):
            yield "Leonardo da Vinci painted the Mona Lisa. "
            yield "The painting is displayed at the Louvre Museum."
            second_generated.set()

    spoken: list[str] = []

    def speak(sentence: str) -> None:
        spoken.append(sentence)
        if len(spoken) == 1:
            assert second_generated.wait(timeout=1.0)

    result = DialogueEngine(StreamingLLM()).respond_stream(
        question="Who painted it and where is it?",
        artwork_chunks=CONTEXT,
        on_sentence=speak,
    )
    assert result.grounded
    assert spoken == [
        "Leonardo da Vinci painted the Mona Lisa.",
        "The painting is displayed at the Louvre Museum.",
    ]
    assert result.response == " ".join(spoken)


def test_ungrounded_stream_is_replaced_before_speech():
    class OffTopicLLM:
        def generate_stream(self, _messages):
            yield "Quantum processors use entanglement for calculations."

    spoken: list[str] = []
    result = DialogueEngine(OffTopicLLM()).respond_stream(
        question="Who painted it?",
        artwork_chunks=CONTEXT,
        on_sentence=spoken.append,
    )
    assert not result.grounded
    assert result.fallback_used
    assert len(spoken) == 1
    assert "verified" in spoken[0]
