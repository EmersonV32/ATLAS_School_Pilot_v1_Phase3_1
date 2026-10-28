"""Prepared invitations must lead to the promised facts without cloud calls."""

import pytest

from atlas.dialogue.dialogue_engine import DialogueEngine
from atlas.dialogue.scripted_faq import (
    _QUESTION_PHRASES,
    PUBLIC_SCRIPTED_LANGUAGES,
    SCRIPTED_FAQ_INTENTS,
    resolve_scripted_faq,
)


class NoCloud:
    def generate(self, _messages):
        raise AssertionError("A prepared invitation must not call the model")


def local_turn(
    engine, question, *, artwork_id="mona_lisa", language="en", profile="adult_beginner"
):
    generation = engine.conversation_generation
    focus = engine.prepare_turn(question, artwork_id)
    result = engine.resolve_local_response(
        question,
        artwork_id=focus.retrieval_artwork_id,
        language=language,
        profile=profile,
        resolved_subject=True,
        expected_generation=generation,
        focus=focus,
    )
    if result is not None:
        assert engine.remember_local_response(
            question,
            result.response,
            artwork_id=focus.artwork_id,
            focus=focus,
            expected_generation=generation,
            follow_up_intent=result.follow_up_intent,
        )
    return result


@pytest.mark.parametrize(
    ("language", "question", "accept", "fact"),
    [
        ("en", "Who painted the Mona Lisa?", "Yes, please", "sfumato"),
        ("fr", "Qui a peint la Joconde ?", "Oui", "sfumato"),
        ("es", "¿Quién pintó la Mona Lisa?", "Sí", "sfumato"),
        ("it", "Chi ha dipinto la Gioconda?", "Sì, grazie", "sfumato"),
        ("zh", "誰畫的？", "好的", "暈塗"),
    ],
)
def test_acceptance_delivers_the_offered_technique_without_a_model(
    language, question, accept, fact
):
    engine = DialogueEngine(NoCloud())
    first = local_turn(engine, question, language=language)
    assert first.intent == "artist"
    assert first.follow_up_intent == "technique"
    assert first.response.startswith(first.base_response)
    second = local_turn(engine, accept, language=language)
    assert second.intent == "technique"
    assert second.artwork_id == "mona_lisa"
    assert fact in second.response
    assert second.response == second.base_response
    assert second.follow_up_intent is None
    assert second.source_ids == first.source_ids
    # A third confirmation must not repeat an already-consumed invitation.
    assert local_turn(engine, accept, language=language) is None


def test_artist_question_then_yes_does_not_repeat_the_artist_biography():
    engine = DialogueEngine(NoCloud())
    first = local_turn(engine, "Who painted this?")
    second = local_turn(engine, "Tell me more")
    expected = resolve_scripted_faq(
        "How was it made?",
        artwork_id="mona_lisa",
        language="en",
        profile="adult_beginner",
        resolved_subject=True,
    )
    assert "Leonardo da Vinci" in first.response
    assert second.base_response == expected.base_response
    assert "sfumato" in second.response
    assert engine._memory.recent[-1].question == "Tell me more"
    assert engine._personalization.completed_turns == 2
    assert engine._memory.turn_number == 2


@pytest.mark.parametrize("language", PUBLIC_SCRIPTED_LANGUAGES)
@pytest.mark.parametrize("intent", SCRIPTED_FAQ_INTENTS)
def test_every_offered_topic_has_a_prepared_continuation(language, intent):
    engine = DialogueEngine(NoCloud())
    first = local_turn(
        engine, _QUESTION_PHRASES[intent][language][0], language=language
    )
    assert first.follow_up_intent
    accept = {"en": "Yes", "fr": "Oui", "es": "Sí", "it": "Sì", "zh": "好的"}
    more = local_turn(engine, accept[language], language=language)
    assert more.intent == first.follow_up_intent
    assert more.response == more.base_response
    assert more.source_ids


@pytest.mark.parametrize("refusal", ["No, thank you", "Non merci"])
def test_decline_invites_a_subject_change_and_consumes_the_offer(refusal):
    engine = DialogueEngine(NoCloud())
    local_turn(engine, "Qui a peint la Joconde ?", language="fr")
    declined = local_turn(engine, refusal, language="fr")
    assert declined.intent == "declined"
    assert "Qu'est-ce qui vous intéresse" in declined.response
    assert "sfumato" not in declined.response
    assert declined.follow_up_intent is None
    assert local_turn(engine, "Oui", language="fr") is None


def test_new_question_replaces_old_invitation_instead_of_hijacking_yes():
    engine = DialogueEngine(NoCloud())
    local_turn(engine, "Who painted this?")
    date = local_turn(engine, "When was it made?")
    assert date.intent == "date"
    assert date.follow_up_intent is None
    assert local_turn(engine, "Yes") is None


def test_camera_change_and_reset_remove_the_previous_offer():
    engine = DialogueEngine(NoCloud())
    local_turn(engine, "Who painted this?")
    assert local_turn(engine, "Yes", artwork_id="starry_night") is None
    local_turn(engine, "Who painted this?")
    old_generation = engine.conversation_generation
    old_focus = engine.prepare_turn("Yes", "mona_lisa")
    engine.reset_conversation()
    assert (
        engine.resolve_local_response(
            "Yes",
            artwork_id="mona_lisa",
            expected_generation=old_generation,
            focus=old_focus,
        )
        is None
    )
    assert not engine.remember_local_response(
        "Yes",
        "A stale answer",
        focus=old_focus,
        expected_generation=old_generation,
        follow_up_intent="detail",
    )
    assert engine._memory.turn_number == 0
    assert local_turn(engine, "Yes") is None


def test_optional_questions_vary_and_remain_available_later_in_the_visit():
    engine = DialogueEngine(NoCloud())
    answers = [
        local_turn(engine, "Qui a peint la Joconde ?", language="fr") for _ in range(7)
    ]
    assert [bool(a.follow_up_intent) for a in answers] == [
        True,
        False,
        True,
        False,
        True,
        False,
        True,
    ]
    invitations = [a.response.removeprefix(a.base_response) for a in answers[::2]]
    assert len(set(invitations[:3])) == 3
    assert all("technique" in question for question in invitations)
    assert all(a.response == a.base_response for a in answers[1::2])


def test_interleaved_model_statements_do_not_repeat_the_last_invitation():
    class StatementsOnly:
        def generate(self, _messages):
            return "Notice the composition."

    engine = DialogueEngine(StatementsOnly())
    first = local_turn(engine, "Who painted this?")
    assert engine._personalization.follow_up_count == 1
    for _ in range(5):
        assert local_turn(engine, "Explain the balance of shapes") is None
        engine.respond("Explain the balance of shapes", [], artwork_id="mona_lisa")
    assert engine._personalization.follow_up_count == 1
    next_offer = local_turn(engine, "Who painted this?")
    assert next_offer.follow_up_intent == first.follow_up_intent
    assert next_offer.response.removeprefix(next_offer.base_response) != (
        first.response.removeprefix(first.base_response)
    )
    assert engine._personalization.follow_up_count == 2
    # Merely resolving an answer must not advance the counter or cadence.
    pending = engine.resolve_local_response("Who painted this?", artwork_id="mona_lisa")
    assert pending.follow_up_intent is None
    assert engine._personalization.follow_up_count == 2
    engine.reset_conversation()
    assert engine._personalization.follow_up_count == 0
    again = local_turn(engine, "Who painted this?")
    assert again.response == first.response
    engine.configure_personalization(interests=["technique"])
    assert engine._personalization.follow_up_count == 0


def test_child_invitation_and_expert_facts_preserve_the_selected_profile():
    engine = DialogueEngine(NoCloud())
    child = local_turn(
        engine, "Qui a peint la Joconde ?", language="fr", profile="child"
    )
    assert "Veux-tu" in child.response
    assert "Voulez-vous" not in child.response
    engine.reset_conversation()
    expert = local_turn(engine, "Who painted this?", profile="expert")
    raw = resolve_scripted_faq(
        "Who painted this?",
        artwork_id="mona_lisa",
        language="en",
        profile="expert",
        resolved_subject=True,
    )
    assert expert.response.startswith(raw.response)
    assert expert.source_ids == raw.source_ids
    assert expert.follow_up_intent == "technique"


class RecordingCloud:
    def __init__(self):
        self.prompts = []

    def generate(self, messages):
        self.prompts.append(messages)
        return "Notice the composition. Would you like to explore its balance?"


def test_model_turn_uses_history_for_variety_and_clears_old_prepared_offer():
    cloud = RecordingCloud()
    engine = DialogueEngine(cloud)
    local_turn(engine, "Who painted this?")
    assert local_turn(engine, "Explain the balance of shapes") is None
    engine.respond("Explain the balance of shapes", [], artwork_id="mona_lisa")
    prompt = str(cloud.prompts[-1])
    assert "PERSONALIZATION QUESTION: NOT REQUESTED" in prompt
    assert "never repeat the same closing question" in prompt
    assert "FOLLOW-UP DIRECTION" in prompt
    assert "Would you like to explore how it was made?" in prompt
    assert local_turn(engine, "Yes") is None
    # The model's actual invitation, even if unrequested, gets breathing room.
    engine.respond("Explain the arrangement of colors", [], artwork_id="mona_lisa")
    assert "PERSONALIZATION QUESTION: NOT REQUESTED" in str(cloud.prompts[-1])
