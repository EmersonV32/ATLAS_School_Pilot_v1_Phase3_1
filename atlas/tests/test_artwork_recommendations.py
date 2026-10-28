"""Recommendation policy receives actual session interests and questions."""

import pytest

from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder


@pytest.mark.parametrize("language", ["en", "fr", "es", "it", "zh"])
@pytest.mark.parametrize("streaming", [False, True])
def test_recommendation_uses_session_evidence_and_one_invitation(language, streaming):
    ctx = DialogueContext(
        question="Recommend another artwork",
        artwork_chunks=[],
        visitor_language=language,
        visitor_interests="colour and light",
        conversation_turns=[("Why did Van Gogh use yellow?", "He explored colour.")],
        topic_artwork_id="sunflowers",
        ask_preference_question=True,
    )
    messages = PromptBuilder().build(ctx, streaming_output=streaming)
    system = messages[0]["content"]
    assert "ARTWORK RECOMMENDATIONS" in system
    assert "Do not invent preferences" in system
    assert "without claiming personalization" in system
    assert "invitation replaces" in system
    assert "physically nearby" in system
    assert "colour and light" in messages[-1]["content"]
    assert any("Why did Van Gogh use yellow?" in m["content"] for m in messages)


@pytest.mark.parametrize(
    "acceptance",
    [
        "Yes, tell me more",
        "Oui, je veux en savoir plus",
        "Si, cuéntame más",
        "Si, dimmi di più",
        "好的",
    ],
)
def test_acceptance_moves_retrieval_to_the_supported_recommended_artwork(acceptance):
    from atlas.dialogue.conversation_memory import ConversationMemory

    memory = ConversationMemory()
    memory.focus("Tell me about Sunflowers", "sunflowers", 0)
    memory.remember(
        "Recommend another artwork",
        "Try The Starry Night. Would you like to know more?",
        "sunflowers",
    )
    focus = memory.focus(acceptance, "sunflowers", 0)
    assert focus.artwork_id == "starry_night"
    assert focus.retrieval_artwork_id == "starry_night"


@pytest.mark.parametrize(
    "answer",
    [
        "Try an Imaginary Unknown Painting. Want more?",
        "Compare The Starry Night and Mona Lisa. Want more?",
    ],
)
def test_unknown_or_ambiguous_recommendation_never_promotes_an_arbitrary_subject(
    answer,
):
    from atlas.dialogue.conversation_memory import ConversationMemory

    memory = ConversationMemory()
    memory.focus("Discuss Sunflowers", None, 0)
    memory.remember("Recommend another artwork", answer, "sunflowers")
    assert memory.focus("Yes", None, 0).artwork_id == "sunflowers"


def test_explicit_question_camera_reset_and_interruption_override_pending():
    from atlas.dialogue.conversation_memory import ConversationMemory

    def prepared():
        memory = ConversationMemory()
        memory.focus("Discuss Sunflowers", "sunflowers", 0)
        memory.remember(
            "Suggest another artwork", "Try The Starry Night. Want more?", "sunflowers"
        )
        return memory

    assert (
        prepared().focus("Tell me about Mona Lisa", "sunflowers", 0).artwork_id
        == "mona_lisa"
    )
    assert (
        prepared().focus("What am I looking at?", "sunflowers", 0).artwork_id
        == "sunflowers"
    )
    memory = prepared()
    memory.focus("Who painted Sunflowers?", "sunflowers", 0)
    assert memory.focus("Yes", "sunflowers", 0).artwork_id == "sunflowers"
    memory = prepared()
    memory.reset()
    assert memory.focus("Yes", None, 1).artwork_id is None


@pytest.mark.parametrize("streaming", [False, True])
def test_model_recommendation_acceptance_uses_new_topic_in_real_engine(streaming):
    from atlas.dialogue.dialogue_engine import DialogueEngine

    class Model:
        def generate(self, messages):
            return "Try The Starry Night for its blue sky. Would you like to know more?"

        def generate_stream(self, messages):
            yield self.generate(messages)

    engine = DialogueEngine(Model())
    engine.prepare_turn("Discuss Sunflowers", "sunflowers")
    if streaming:
        engine.respond_stream(
            "Recommend another artwork",
            [],
            on_sentence=lambda _: None,
            artwork_id="sunflowers",
        )
    else:
        engine.respond("Recommend another artwork", [], artwork_id="sunflowers")
    assert (
        engine.prepare_turn("Yes, tell me more", "sunflowers").retrieval_artwork_id
        == "starry_night"
    )


def test_recommendation_reason_can_mention_the_previous_artwork():
    from atlas.dialogue.conversation_memory import ConversationMemory

    memory = ConversationMemory()
    memory.focus("Discuss Sunflowers", "sunflowers", 0)
    memory.remember(
        "Recommend another artwork",
        "Since you liked Sunflowers, try The Starry Night. Want to know more?",
        "sunflowers",
    )
    assert memory.focus("Yes", "sunflowers", 0).artwork_id == "starry_night"
