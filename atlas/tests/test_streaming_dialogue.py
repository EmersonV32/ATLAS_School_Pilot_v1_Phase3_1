"""Tests for concurrent sentence-level LLM to TTS streaming."""

from __future__ import annotations

import threading

from atlas.dialogue.dialogue_engine import UNGROUNDED_FALLBACK, DialogueEngine
from atlas.dialogue.sentence_stream import SentenceAssembler

CONTEXT = [
    {
        "chunk_id": "mona-1",
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


def test_ungrounded_stream_uses_safe_fallback_before_speech():
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
    assert spoken == [UNGROUNDED_FALLBACK["en"]]
    assert "Quantum processors" not in result.response


def test_structured_stream_validates_claims_and_chunk_ids_before_speech():
    class StructuredLLM:
        def generate(self, _messages):
            return (
                '{"spoken_answer":"Quantum processors explain this painting.",'
                '"used_chunk_ids":["mona-1","invented"],"confidence":"high",'
                '"unsupported_claims":["quantum claim"],"fallback_used":false}'
            )

    spoken: list[str] = []
    result = DialogueEngine(StructuredLLM(), expect_json=True).respond_stream(
        question="Who painted it?",
        artwork_chunks=CONTEXT,
        on_sentence=spoken.append,
    )

    assert spoken == [UNGROUNDED_FALLBACK["en"]]
    assert result.grounding_reason == "unsupported_claims"
    assert result.used_chunk_ids == ["mona-1"]
    assert result.fallback_used is True


def test_streaming_response_stops_before_another_sentence_after_cancel():
    cancel = threading.Event()

    class StreamingLLM:
        def generate_stream(self, _messages):
            yield "Leonardo da Vinci painted the Mona Lisa. "
            yield "The painting is displayed at the Louvre Museum."

    spoken: list[str] = []

    def speak(sentence: str) -> None:
        spoken.append(sentence)
        cancel.set()

    result = DialogueEngine(StreamingLLM()).respond_stream(
        question="Who painted it and where is it?",
        artwork_chunks=CONTEXT,
        on_sentence=speak,
        cancel_event=cancel,
    )

    assert result.error == "interaction_cancelled"
    assert spoken == ["Leonardo da Vinci painted the Mona Lisa."]


def test_cancelled_stream_cannot_repopulate_a_reset_conversation():
    started = threading.Event()
    release = threading.Event()

    class BlockedLLM:
        def generate_stream(self, _messages):
            started.set()
            release.wait(timeout=1.0)
            yield "Leonardo da Vinci painted the Mona Lisa."

    engine = DialogueEngine(BlockedLLM())
    cancel = threading.Event()
    result_holder = []
    caller = threading.Thread(
        target=lambda: result_holder.append(
            engine.respond_stream(
                question="old-session question",
                artwork_chunks=CONTEXT,
                on_sentence=lambda _sentence: None,
                cancel_event=cancel,
            )
        )
    )
    caller.start()
    assert started.wait(timeout=1.0)
    cancel.set()
    caller.join(timeout=1.0)
    assert result_holder[0].error == "interaction_cancelled"

    engine.reset_conversation()
    cancel.clear()
    release.set()
    workers = [
        thread
        for thread in threading.enumerate()
        if thread.name == "atlas-llm-stream"
    ]
    for worker in workers:
        worker.join(timeout=1.0)

    assert engine._conversation_turns == []


def test_cancelled_structured_worker_cannot_repopulate_a_reset_conversation():
    started = threading.Event()
    release = threading.Event()

    class BlockedStructuredLLM:
        def generate(self, _messages):
            started.set()
            release.wait(timeout=1.0)
            return (
                '{"spoken_answer":"Leonardo da Vinci painted the Mona Lisa.",'
                '"used_chunk_ids":["mona-1"],"confidence":"high",'
                '"unsupported_claims":[],"fallback_used":false}'
            )

    engine = DialogueEngine(BlockedStructuredLLM(), expect_json=True)
    cancel = threading.Event()
    result_holder = []
    caller = threading.Thread(
        target=lambda: result_holder.append(
            engine.respond_stream(
                question="old structured question",
                artwork_chunks=CONTEXT,
                on_sentence=lambda _sentence: None,
                cancel_event=cancel,
            )
        )
    )
    caller.start()
    assert started.wait(timeout=1.0)
    cancel.set()
    caller.join(timeout=1.0)
    assert result_holder[0].error == "interaction_cancelled"

    engine.reset_conversation()
    cancel.clear()
    release.set()
    workers = [
        thread
        for thread in threading.enumerate()
        if thread.name == "atlas-llm-structured-stream"
    ]
    for worker in workers:
        worker.join(timeout=1.0)

    assert engine._conversation_turns == []
