"""A disobedient model cannot replace the local English/French wake greeting."""

from __future__ import annotations

import json

import pytest

from atlas.dashboard.visitor_activation import local_greeting
from atlas.dialogue.dialogue_engine import DialogueEngine
from atlas.dialogue.introduction_policy import (
    introduction_fallback,
    without_model_introduction,
)

ART_FACT = "Leonardo da Vinci painted the Mona Lisa."
FR_FACT = "Léonard de Vinci a peint la Joconde."


@pytest.mark.parametrize(
    ("prefix", "fact"),
    [
        ("Hello. I'm ATLAS.", ART_FACT),
        ("Hello! I’m ATLAS, your museum guide.", ART_FACT),
        ("I am ATLAS, a museum guide.", ART_FACT),
        ("My name is ATLAS.", ART_FACT),
        ("Bonjour. Je suis ATLAS.", FR_FACT),
        ("Bonjour, je m'appelle ATLAS.", FR_FACT),
        ("Je m’appelle ATLAS, votre guide.", FR_FACT),
        ("Je me présente : ATLAS, votre guide.", FR_FACT),
        ("Je me présente, je suis ATLAS.", FR_FACT),
        ("Je me présente. Je suis ATLAS.", FR_FACT),
    ],
)
def test_explicit_intro_sentences_are_removed_and_useful_answer_retained(prefix, fact):
    assert without_model_introduction(prefix + " " + fact) == fact


@pytest.mark.parametrize(
    "text",
    [
        "ATLAS can answer questions about the Mona Lisa.",
        "The words 'I am ATLAS' are a self-introduction.",
        '"Bonjour Atlas" is a wake phrase.',
        "Bonjour is a French greeting.",
        "Atlas is a figure from Greek mythology.",
        "Je suis intéressé par la Joconde.",
        "I'm interested in Leonardo's technique.",
    ],
)
def test_artwork_content_and_quoted_or_third_person_references_are_preserved(text):
    assert without_model_introduction(text) == text


def test_intro_after_the_useful_answer_is_also_removed():
    assert without_model_introduction(ART_FACT + " I am ATLAS.") == ART_FACT


@pytest.mark.parametrize("structured", [False, True])
@pytest.mark.parametrize("language,fact", [("en", ART_FACT), ("fr", FR_FACT)])
def test_full_model_answer_and_memory_exclude_introduction(structured, language, fact):
    class Model:
        def generate(self, _messages):
            answer = "Bonjour. Je suis ATLAS. " + fact
            return json.dumps({"spoken_answer": answer}) if structured else answer

    engine = DialogueEngine(Model(), expect_json=structured)
    result = engine.respond("Tell me a fact", [{"text": fact}], language=language)

    assert result.response == fact
    assert result.filtered is False
    assert engine._conversation_turns == [("Tell me a fact", fact)]


@pytest.mark.parametrize("punctuated", [False, True])
def test_stream_discards_intro_before_callback_and_keeps_useful_text(punctuated):
    class Model:
        def generate_stream(self, _messages):
            yield "Hello. I’m AT"
            yield "LAS. "
            yield ART_FACT if punctuated else ART_FACT.rstrip(".")

    spoken = []
    engine = DialogueEngine(Model())
    result = engine.respond_stream(
        "Tell me a fact", [{"text": ART_FACT}], on_sentence=spoken.append
    )
    expected = ART_FACT if punctuated else ART_FACT.rstrip(".")
    assert spoken == [expected]
    assert result.response == expected
    assert result.filtered is False
    assert engine._conversation_turns == [("Tell me a fact", expected)]


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("ending", [".", ""])
def test_intro_only_answer_gets_one_non_introductory_fallback(
    streaming, language, ending
):
    class Model:
        def generate(self, _messages):
            return "Bonjour. Je m’appelle ATLAS" + ending

        def generate_stream(self, messages):
            yield self.generate(messages)

    spoken = []
    engine = DialogueEngine(Model())
    result = (
        engine.respond_stream(
            "What can you do?", [], on_sentence=spoken.append, language=language
        )
        if streaming else engine.respond("What can you do?", [], language=language)
    )
    assert result.response == introduction_fallback(language)
    assert result.fallback_used is True
    assert result.filtered is False
    if streaming:
        assert spoken == [result.response]


def test_local_name_bearing_wake_greeting_remains_intact():
    assert "Emerson, I'm ATLAS, your AI art guide." in local_greeting("en", "Emerson")
    assert local_greeting("fr", "Emerson").startswith(
        "Bonjour Emerson, je suis ATLAS, votre guide artistique virtuel."
    )


def test_intro_cleanup_preserves_conversation_artwork_subject():
    class Model:
        def generate(self, _messages):
            return "Hello, I am ATLAS. " + ART_FACT

    engine = DialogueEngine(Model())
    result = engine.respond(
        "Tell me about the Mona Lisa", [{"text": ART_FACT}],
        artwork_id="mona_lisa",
    )
    assert result.response == ART_FACT
    assert engine._memory.topic == "mona_lisa"
    assert engine._memory.recent[-1].artwork_id == "mona_lisa"
    assert engine._memory.recent[-1].answer == ART_FACT
