"""Coverage for the local multilingual scripted-answer path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atlas.dialogue.scripted_faq import (
    _QUESTION_PHRASES,
    PUBLIC_SCRIPTED_LANGUAGES,
    SCRIPTED_FAQ_INTENTS,
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
    question = _QUESTION_PHRASES[intent][language][0]
    assert match_scripted_intent(question, language) == intent


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
