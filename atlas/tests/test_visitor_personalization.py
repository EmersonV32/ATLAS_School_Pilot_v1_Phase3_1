"""Wake activation and session-only personalization tests."""

from __future__ import annotations

import pytest

from atlas.dashboard.visitor_activation import (
    clean_greeting_name,
    local_greeting,
    wake_phrase_matches,
)
from atlas.dialogue.personalization import SessionPersonalization


@pytest.mark.parametrize(
    ("language", "phrase"),
    [
        ("en", "Hello ATLAS"),
        ("fr", "Bonjour Atlas !"),
        ("es", "Hola ATLAS"),
        ("it", "Ciao Atlas"),
        ("zh-Hant", "你好 ATLAS"),
    ],
)
def test_wake_phrase_uses_the_selected_visitor_language(language, phrase):
    assert wake_phrase_matches(phrase, language) is True


def test_unrelated_speech_does_not_activate_atlas():
    assert wake_phrase_matches("Tell me about this painting", "en") is False
    assert wake_phrase_matches("Hello ATLAS", "fr") is False


def test_local_greeting_uses_the_optional_name_without_persisting_it():
    name = clean_greeting_name("  Émerson-Li  ")
    greeting = local_greeting("en", name)
    assert greeting.startswith("Hi Émerson-Li, I'm ATLAS.")
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
