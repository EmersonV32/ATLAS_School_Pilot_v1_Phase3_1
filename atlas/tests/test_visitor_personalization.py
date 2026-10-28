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


@pytest.mark.parametrize("language", ["en", "fr", "es", "it", "zh"])
def test_name_does_not_remove_any_of_the_full_introduction(language):
    anonymous = session_introduction(language)
    named = session_introduction(language, "Emerson")
    # Only the opening changes; the full guide explanation remains verbatim.
    assert named.split("ATLAS", 1)[1] == anonymous.split("ATLAS", 1)[1]
    assert named.count("Emerson") == 1
    assert "Emerson" not in anonymous
    assert named.count("ATLAS") == anonymous.count("ATLAS") == 1


@pytest.mark.parametrize(
    ("language", "role", "help_text", "invitation"),
    [
        ("en", "your AI art guide", "I can help you discover artworks",
         "Are you interested"),
        ("fr", "votre guide artistique virtuel", "Je peux vous faire découvrir",
         "Est-ce qu'un artiste"),
    ],
)
@pytest.mark.parametrize("name", [None, "", "Emerson"])
def test_full_introduction_finishes_before_interest_question(
    language, role, help_text, invitation, name
):
    introduction = session_introduction(language, name)
    assert introduction.index("ATLAS") < introduction.index(role)
    assert introduction.index(role) < introduction.index(help_text)
    assert introduction.index(help_text) < introduction.index(invitation)
    assert introduction.count("?") == 1
    assert introduction.endswith("?")
    assert ("Emerson" in introduction) is bool(name)


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
    assert greeting.startswith("Hey Émerson-Li, I'm ATLAS, your AI art guide.")
    assert "I can help you discover artworks" in greeting
    assert greeting.endswith(
        "Are you interested in an artist or the story behind an artwork?"
    )


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
