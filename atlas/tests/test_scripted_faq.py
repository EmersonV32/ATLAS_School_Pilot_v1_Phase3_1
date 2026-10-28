"""Coverage for the local multilingual scripted-answer path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atlas.dialogue.scripted_faq import (
    _ARTWORKS,
    _COMPLETE_QUESTIONS,
    _EXACT_STANDALONE_QUESTIONS,
    _QUESTION_PHRASES,
    PUBLIC_SCRIPTED_LANGUAGES,
    SCRIPTED_FAQ_INTENTS,
    is_exact_scripted_question,
    match_scripted_intent,
    resolve_scripted_faq,
    scripted_catalog_artwork_ids,
)
from atlas.models.enums import EducationalLevel

PACK_DIR = (
    Path(__file__).resolve().parent.parent / "data" / "content_packs" / "demo_pack"
)


def test_scripted_catalog_covers_every_demo_pack_artwork():
    manifest = json.loads((PACK_DIR / "manifest.json").read_text(encoding="utf-8"))
    pack_ids = {
        json.loads((PACK_DIR / filename).read_text(encoding="utf-8"))["artwork_id"]
        for filename in manifest["artwork_files"]
    }
    assert scripted_catalog_artwork_ids() == pack_ids


def test_every_scripted_source_id_exists_on_its_content_pack_artwork():
    manifest = json.loads((PACK_DIR / "manifest.json").read_text(encoding="utf-8"))
    for filename in manifest["artwork_files"]:
        artwork = json.loads((PACK_DIR / filename).read_text(encoding="utf-8"))
        result = resolve_scripted_faq(
            "Who painted this?",
            artwork_id=artwork["artwork_id"],
            language="en",
            profile="adult_beginner",
        )
        assert result is not None
        declared_source_ids = {source["source_id"] for source in artwork["sources"]}
        assert set(result.source_ids) <= declared_source_ids


@pytest.mark.parametrize("language", PUBLIC_SCRIPTED_LANGUAGES)
@pytest.mark.parametrize("intent", SCRIPTED_FAQ_INTENTS)
def test_every_scripted_question_is_available_in_every_public_language(
    language, intent
):
    for question in _QUESTION_PHRASES[intent][language]:
        assert match_scripted_intent(question, language) == intent, question


@pytest.mark.parametrize("language", PUBLIC_SCRIPTED_LANGUAGES)
@pytest.mark.parametrize("intent", SCRIPTED_FAQ_INTENTS)
@pytest.mark.parametrize("artwork_id", tuple(sorted(scripted_catalog_artwork_ids())))
def test_every_named_question_form_uses_its_named_artwork(language, intent, artwork_id):
    title = _ARTWORKS[artwork_id]["title"][language]
    for template in _COMPLETE_QUESTIONS[language][intent]:
        question = template.replace("artwork", title)
        result = resolve_scripted_faq(
            question,
            artwork_id="sunflowers" if artwork_id != "sunflowers" else "mona_lisa",
            language=language,
            profile="adult_beginner",
        )
        assert result is not None, question
        assert result.intent == intent, question
        assert result.artwork_id == artwork_id, question
        assert is_exact_scripted_question(question, language), question


def test_who_is_the_mona_lisa_answers_the_subject_without_camera_context():
    result = resolve_scripted_faq(
        "Who is the Mona Lisa?",
        artwork_id=None,
        language="en",
        profile="adult_beginner",
    )
    assert result is not None
    assert result.artwork_id == "mona_lisa"
    assert result.intent == "subject"
    assert "Lisa Gherardini" in result.response
    assert "src_ml_louvre_gallery" in result.source_ids


@pytest.mark.parametrize(
    "question",
    (
        "When was the Mona Lisa stolen?",
        "When was the Mona Lisa treated?",
        "What year was the Mona Lisa cleaned?",
        "Who painted over the crack during restoration?",
        "What year was the protective glass installed?",
        "Where is it in the Thirty-six Views series?",
        "How was it made famous by the theft?",
        "Who painted this—actually, don't tell me the artist; "
        "tell me who restored it most recently.",
        "Who painted Guernica?",
        "Who painted the Mona Lisa and Starry Night?",
        "Why is the Mona Lisa smiling?",
        "What materials were used for the frame of the Mona Lisa?",
    ),
)
def test_specific_unknown_and_multiple_artwork_questions_use_deeper_path(question):
    assert resolve_scripted_faq(
        question,
        artwork_id="mona_lisa",
        language="en",
        profile="adult_beginner",
    ) is None


@pytest.mark.parametrize(
    ("question", "language"),
    (
        ("What does sfumato mean in Mona Lisa?", "en"),
        ("Define the word portrait in Mona Lisa.", "en"),
        ("Que signifie le mot sfumato dans la Joconde ?", "fr"),
    ),
)
def test_named_artwork_does_not_override_the_vocabulary_route(question, language):
    assert resolve_scripted_faq(
        question,
        artwork_id="mona_lisa",
        language=language,
        profile="child",
    ) is None


def test_resolved_camera_subject_wins_over_a_guessed_title():
    result = resolve_scripted_faq(
        "What am I looking at, is it Mona Lisa?",
        artwork_id="starry_night",
        language="en",
        profile="adult_beginner",
        resolved_subject=True,
    )
    assert result is not None
    assert result.artwork_id == "starry_night"
    assert result.intent == "identify"
    assert "Starry Night" in result.response


@pytest.mark.parametrize("language", PUBLIC_SCRIPTED_LANGUAGES)
@pytest.mark.parametrize("profile", tuple(level.value for level in EducationalLevel))
@pytest.mark.parametrize("intent", SCRIPTED_FAQ_INTENTS)
@pytest.mark.parametrize("artwork_id", tuple(sorted(scripted_catalog_artwork_ids())))
def test_every_artwork_language_profile_and_intent_has_an_answer(
    language, profile, intent, artwork_id
):
    result = resolve_scripted_faq(
        _QUESTION_PHRASES[intent][language][0],
        artwork_id=artwork_id,
        language=language,
        profile=profile,
    )

    assert result is not None
    assert result.artwork_id == artwork_id
    assert result.intent == intent
    assert result.response.strip()
    assert result.base_response.strip()
    assert result.response.startswith(result.base_response)
    assert result.follow_up_intent in SCRIPTED_FAQ_INTENTS
    assert result.source_ids
    if language != "en":
        assert "Would you" not in result.response


def test_close_paraphrase_and_named_artwork_work_without_camera_context():
    assert match_scripted_intent("Who painteed this picture?", "en") == "artist"
    result = resolve_scripted_faq(
        "Who painteed the Mona Lisa?",
        artwork_id=None,
        language="en",
        profile="adult_beginner",
    )
    assert result is not None
    assert result.artwork_id == "mona_lisa"
    assert "Leonardo da Vinci" in result.response


@pytest.mark.parametrize(
    "question",
    (
        "Where is the bathroom?",
        "What should I do next?",
        "What is the weather?",
        "Who made this museum?",
    ),
)
def test_unrelated_questions_do_not_trigger_scripted_artwork_answers(question):
    assert match_scripted_intent(question, "en") is None


def test_traditional_chinese_is_recognized_and_returned():
    result = resolve_scripted_faq(
        "這件作品是誰畫的？",
        artwork_id="mona_lisa",
        language="zh-Hant",
        profile="adult_beginner",
    )
    assert result is not None
    assert result.intent == "artist"
    assert "這件作品" in result.response
    assert "誰" not in result.response
    assert "这件作品" not in result.response


def test_deictic_faq_without_artwork_asks_for_clarification():
    result = resolve_scripted_faq(
        "Who painted this?",
        artwork_id=None,
        language="en",
        profile="adult_beginner",
    )
    assert result is not None
    assert result.artwork_id is None
    assert result.response == "Which artwork are you looking at?"
    assert result.base_response == result.response
    assert result.follow_up_intent is None


def test_unmatched_question_and_preview_language_use_deeper_path():
    assert (
        resolve_scripted_faq(
            "Compare its composition with another work.",
            artwork_id="mona_lisa",
            language="en",
            profile="expert",
        )
        is None
    )
    assert match_scripted_intent("من رسم هذه اللوحة؟", "ar") is None


def test_specific_material_question_wins_over_generic_identification_phrase():
    assert match_scripted_intent("What is this made of?", "en") == "technique"


def test_early_child_and_expert_answers_are_not_the_same():
    question = "How was it made?"
    child = resolve_scripted_faq(
        question,
        artwork_id="mona_lisa",
        language="en",
        profile="early_child",
    )
    expert = resolve_scripted_faq(
        question,
        artwork_id="mona_lisa",
        language="en",
        profile="expert",
    )
    assert child is not None and expert is not None
    assert child.response != expert.response
    assert child.response.endswith("Want an easy example?")
    assert "poplar panel" in expert.response


def test_early_child_and_adult_follow_ups_use_different_language():
    child = resolve_scripted_faq(
        "Who painted this?",
        artwork_id="mona_lisa",
        language="en",
        profile="early_child",
    )
    adult = resolve_scripted_faq(
        "Who painted this?",
        artwork_id="mona_lisa",
        language="en",
        profile="adult_beginner",
    )

    assert child is not None and adult is not None
    assert child.response.endswith("Want to hear how they made it?")
    assert adult.response.endswith("Would you like to know how it was made?")


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("C'est quoi la Joconde ?", "identify"),
        ("En quelle année la Joconde a été peinte ?", "date"),
        ("Quand est-ce que la Joconde a été peinte ?", "date"),
        ("Comment la Joconde a été réalisée ?", "technique"),
        ("Qu'est-ce qu'elle représente ?", "subject"),
        ("Quand est-ce qu'elle a été faite ?", "date"),
        ("Quand est-ce qu'il a été peint ?", "date"),
        ("Comment elle a été réalisée ?", "technique"),
        ("Comment il a été fait ?", "technique"),
        ("C'est quoi cette œuvre ?", "identify"),
    ],
)
def test_common_spoken_french_forms_use_prepared_answer(question, intent):
    result = resolve_scripted_faq(
        question, artwork_id="mona_lisa", language="fr", profile="adult_beginner"
    )
    assert result is not None
    assert result.artwork_id == "mona_lisa"
    assert result.intent == intent
    assert is_exact_scripted_question(question, "fr")


@pytest.mark.parametrize(
    "question", ["Qui est-il ?", "Qui est-elle ?", "Pourquoi il est célèbre ?"]
)
def test_french_person_pronouns_do_not_invent_an_artwork_subject(question):
    assert not is_exact_scripted_question(question, "fr")
    assert resolve_scripted_faq(
        question, artwork_id="mona_lisa", language="fr", profile="adult_beginner"
    ) is None


def test_french_artist_then_person_identity_keeps_history_aware_fallback():
    from atlas.dialogue.dialogue_engine import DialogueEngine

    class NoCloud:
        def generate(self, _messages):
            raise AssertionError("Only the local-routing decision is under test")

    engine = DialogueEngine(NoCloud())
    question = "Qui a peint la Joconde ?"
    focus = engine.prepare_turn(question, "mona_lisa")
    artist = engine.resolve_local_response(
        question, artwork_id=focus.retrieval_artwork_id, language="fr", focus=focus,
        resolved_subject=True,
    )
    assert artist is not None and artist.intent == "artist"
    assert "Leonardo da Vinci" in artist.base_response
    assert engine.remember_local_response(
        question, artist.response, focus=focus,
        follow_up_intent=artist.follow_up_intent,
    )
    followup = "Qui est-il ?"
    followup_focus = engine.prepare_turn(followup, "mona_lisa")
    assert engine.resolve_local_response(
        followup, artwork_id=followup_focus.retrieval_artwork_id, language="fr",
        focus=followup_focus, resolved_subject=True,
    ) is None
    assert not is_exact_scripted_question(followup, "fr")
    assert engine._memory.recent[-1].answer == artist.response


@pytest.mark.parametrize(
    ("question", "language"),
    [
        ("Who is the Mona Lisa?", "en"),
        ("Who painted this?", "en"),
        ("When was this created?", "en"),
        ("Qui a peint la Joconde ?", "fr-CA"),
        ("¿Quién pintó la Mona Lisa?", "es"),
        ("Chi ha dipinto la Gioconda?", "it"),
        ("這件作品是誰畫的？", "zh-Hant"),
    ],
)
def test_stt_exact_predicate_accepts_complete_finite_questions(question, language):
    assert is_exact_scripted_question(question, language)


@pytest.mark.parametrize("language", PUBLIC_SCRIPTED_LANGUAGES)
def test_every_vetted_standalone_question_has_a_prepared_answer(language):
    for question in _EXACT_STANDALONE_QUESTIONS[language]:
        assert is_exact_scripted_question(question, language), question
        result = resolve_scripted_faq(
            question, artwork_id="mona_lisa", language=language,
            profile="adult_beginner",
        )
        assert result is not None, question
        assert result.artwork_id == "mona_lisa", question


@pytest.mark.parametrize(
    ("question", "language"),
    [
        ("Who painted", "en"),
        ("what year", "en"),
        ("when was", "en"),
        ("when did the artist", "en"),
        ("Qui a peint", "fr"),
        ("Quelle année", "fr"),
        ("Who painteed this picture?", "en"),
        ("Who painted this and", "en"),
        ("Who painted this and why?", "en"),
        ("Who painted this, actually tell me who restored it", "en"),
        ('"Who painted this?"', "en"),
        ("'Who painted this?'", "en"),
        ("Who painted this? Tell me more", "en"),
        ("When was the Mona Lisa stolen?", "en"),
        ("Quand est-ce que la Joconde a été volée ?", "fr"),
        ("What year was the protective glass installed?", "en"),
        ("Who painted this?", "ar"),
        ("Who painted this?", "xx"),
        ("Who painted this?", ""),
    ],
)
def test_stt_exact_predicate_rejects_fragments_fuzzy_quotes_and_deep_questions(
    question, language
):
    assert not is_exact_scripted_question(question, language)


@pytest.mark.parametrize("language", PUBLIC_SCRIPTED_LANGUAGES)
@pytest.mark.parametrize("profile", ["adult_beginner", "child", "expert"])
def test_base_response_metadata_preserves_facts_without_legacy_invitation(
    language, profile
):
    result = resolve_scripted_faq(
        _QUESTION_PHRASES["artist"][language][1],
        artwork_id="mona_lisa", language=language, profile=profile,
    )
    assert result is not None
    assert result.base_response
    assert result.response.startswith(result.base_response)
    assert result.follow_up_intent == "technique"
    assert _ARTWORKS["mona_lisa"]["artist"] in result.base_response
    if profile == "expert":
        assert result.base_response == result.response
    else:
        assert result.base_response != result.response
