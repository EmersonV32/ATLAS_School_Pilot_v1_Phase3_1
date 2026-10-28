"""Wake activation and session-only personalization tests."""

from __future__ import annotations

import pytest

from atlas.dashboard.visitor_activation import (
    clean_greeting_name,
    local_greeting,
    session_introduction,
    wake_phrase_matches,
)
from atlas.dialogue.personalization import SessionPersonalization
from atlas.models.languages import ADMIN_LANGUAGE_CODES


@pytest.mark.parametrize("language", sorted(ADMIN_LANGUAGE_CODES))
def test_session_introduction_covers_every_enabled_admin_language(language):
    introduction = session_introduction(language)
    assert introduction
    assert introduction != session_introduction("en") or language == "en"


def test_named_introduction_is_one_local_greeting():
    assert session_introduction("fr", "Emerson") == local_greeting("fr", "Emerson")


@pytest.mark.parametrize("language", sorted(ADMIN_LANGUAGE_CODES))
@pytest.mark.parametrize("phrase", ["Hey ATLAS", "Bonjour Atlas !", "  HEY, Atlas. "])
def test_only_explicit_wake_greetings_work_in_every_visitor_language(language, phrase):
    assert wake_phrase_matches(phrase, language) is True


@pytest.mark.parametrize(
    "phrase",
    [
        "Tell me about this painting",
        "Hello ATLAS",
        "Hi Atlas",
        "Salut Atlas",
        "Hola ATLAS",
        "Ciao Atlas",
        "你好 ATLAS",
        "Hey Atlas, who painted the Mona Lisa?",
        "Bonjour Atlas, quelle est cette œuvre ?",
        "Do I say Hey Atlas?",
        "Hey Atlas um",
        "",
    ],
)
def test_other_greetings_mentions_and_questions_do_not_activate_atlas(phrase):
    assert wake_phrase_matches(phrase, "en") is False


def test_local_greeting_uses_the_optional_name_without_persisting_it():
    name = clean_greeting_name("  Émerson-Li  ")
    greeting = local_greeting("en", name)
    assert greeting.startswith("Hey Émerson-Li, I'm ATLAS.")
    assert "ask me anything" in greeting


@pytest.mark.parametrize("value", ["Ada 123", "<script>", "A/B", "A_B"])
def test_greeting_name_rejects_non_name_characters(value):
    with pytest.raises(ValueError):
        clean_greeting_name(value)


def test_session_profile_learns_only_allowlisted_preferences():
    profile = SessionPersonalization()
    profile.configure(interests=["technique"], accessibility=[])
    assert profile.should_ask_preference_question() is True
    profile.complete_turn(preference_question_requested=True)

    profile.observe("History, and please keep it brief.")
    interests, styles = profile.prompt_lines()
    assert "historical context" in interests
    assert "brief answers" in styles
    assert not hasattr(profile, "name")


def test_session_profile_ignores_unprompted_free_form_personal_data():
    profile = SessionPersonalization()
    profile.configure()
    profile.observe("My name is Emerson and I live in Montreal")
    assert profile.prompt_lines() == ("none stated", "none stated")


def test_session_profile_reset_clears_all_learned_preferences():
    profile = SessionPersonalization()
    profile.configure(interests=["symbols"], accessibility=["slower_pace"])
    profile.complete_turn(preference_question_requested=True)
    profile.observe("I prefer detailed answers")
    profile.reset()
    assert profile.prompt_lines() == ("none stated", "none stated")
    assert profile.completed_turns == 0
