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


def test_dev_stream_records_low_overlap_without_blocking_general_knowledge():
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
    assert not result.fallback_used
    assert len(spoken) == 1
    assert spoken[0].startswith("Quantum processors")


def test_gemini_stream_path_validates_structured_output_before_speech():
    class StructuredLLM:
        def generate(self, _messages, max_tokens=300):
            return (
                '{"spoken_answer": "Leonardo da Vinci painted the Mona Lisa.", '
                '"used_chunk_ids": [], "confidence": "high", '
                '"unsupported_claims": [], "fallback_used": false}'
            )

        def generate_stream(self, _messages):
            raise AssertionError("unsafe text streaming path was used")

    spoken: list[str] = []
    result = DialogueEngine(StructuredLLM(), expect_json=True).respond_stream(
        question="Who painted it?",
        artwork_chunks=CONTEXT,
        on_sentence=spoken.append,
    )
    assert result.grounded
    assert spoken == ["Leonardo da Vinci painted the Mona Lisa."]
