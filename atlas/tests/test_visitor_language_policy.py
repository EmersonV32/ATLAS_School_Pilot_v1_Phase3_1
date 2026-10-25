"""Synthetic regressions for wake timing, plain language and word questions."""

import pytest

from atlas.dashboard.visitor_activation import (
    is_hesitation_only,
    wake_phrase_matches,
    wake_phrase_remainder,
)
from atlas.dialogue.personalization import SessionPersonalization
from atlas.dialogue.plain_faq import plain_catalog_languages, plain_facts
from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder
from atlas.dialogue.scripted_faq import (
    PUBLIC_SCRIPTED_LANGUAGES,
    resolve_scripted_faq,
    scripted_catalog_artwork_ids,
)
from atlas.dialogue.vocabulary import asks_word_meaning
from atlas.models.languages import OUTPUT_LANGUAGE_NAMES


def test_familiar_hey_atlas_address_is_recognized_in_french():
    assert wake_phrase_matches("Hey Atlas", "fr")


@pytest.mark.parametrize("profile", ["early_child", "child", "simple_language"])
def test_french_sunflowers_uses_everyday_words_instead_of_art_jargon(profile):
    answer = resolve_scripted_faq(
        "Quelle technique ?",
        artwork_id="sunflowers", language="fr", profile=profile,
    )
    assert answer is not None
    assert "épaisse" in answer.response
    assert "dépasse" in answer.response
    assert "relief" not in answer.response.casefold()
    assert "empâtement" not in answer.response.casefold()


@pytest.mark.parametrize("profile", ["child", "adult_beginner", "expert"])
def test_word_definition_does_not_get_a_canned_whole_artwork_meaning(profile):
    assert resolve_scripted_faq(
        "What does impasto mean?", artwork_id="sunflowers",
        language="en", profile=profile,
    ) is None


def test_child_policy_has_priority_over_learned_technical_preference():
    messages = PromptBuilder().build(DialogueContext(
        question="Explain how this was painted.", artwork_chunks=[],
        profile="child", visitor_language="fr",
        explanation_preferences="technical art vocabulary",
    ))
    system = messages[0]["content"]
    assert "PLAIN LANGUAGE PRIORITY" in system
    assert "thick paint that sticks out" in system
    assert "technical-style preferences" in system


@pytest.mark.parametrize("profile", ["child", "adult_beginner", "expert"])
def test_every_level_has_contextual_vocabulary_help(profile):
    messages = PromptBuilder().build(DialogueContext(
        question="Que veut dire ce mot ?", artwork_chunks=[],
        profile=profile, visitor_language="fr",
    ))
    assert "VOCABULARY HELP" in messages[0]["content"]
    assert "earlier artwork" in messages[0]["content"]


@pytest.mark.parametrize("language", tuple(OUTPUT_LANGUAGE_NAMES))
def test_every_admin_language_keeps_child_guidance(language):
    messages = PromptBuilder().build(DialogueContext(
        question="Explain this", artwork_chunks=[], profile="child",
        visitor_language=language,
    ))
    assert "PLAIN LANGUAGE PRIORITY" in messages[0]["content"]
    assert OUTPUT_LANGUAGE_NAMES[language] in messages[-1]["content"]
    assert len(messages[-1]["content"].split("VISITOR QUESTION:")[-1]) > 50


@pytest.mark.parametrize(("text", "language", "remainder"), [
    ("Bonjour Atlas", "fr", ""),
    ("Hey Atlas… euh", "fr", ""),
    ("Bonjour, ATLAS ! Qui a peint la Joconde ?", "fr", "Qui a peint la Joconde ?"),
    ("Hey Atlas, what does relief mean?", "en", "what does relief mean?"),
    ("Hola Atlas, ¿qué significa esta palabra?", "es", "¿qué significa esta palabra?"),
    ("你好Atlas這個詞是什麼意思？", "zh", "這個詞是什麼意思?"),
    ("Hey Atlasian", "en", None),
    ("Hello Atlas", "fr", None),
    ("I said hello Atlas yesterday", "en", None),
])
def test_wake_prefix_preserves_the_question(text, language, remainder):
    assert wake_phrase_remainder(text, language) == remainder


@pytest.mark.parametrize("text", ["euh", "um… uh", "", "…"])
def test_fillers_keep_the_listening_turn_open(text):
    assert is_hesitation_only(text)


@pytest.mark.parametrize("text", [
    "What does relief mean?", "Que signifie empâtement ?",
    "Explique-moi le mot relief.", "Que veut dire ce mot ?",
    "Ça veut dire quoi sfumato ?", "What do you mean by composition?",
    "What is impasto?", "¿Qué significa relieve?", "Cosa significa impasto?",
    "這個詞是什麼意思？", "Why did you use that word for this painting?",
    "What is the meaning of impasto?", "What's the meaning of relief?",
    "C'est quoi le relief ?", "Que signifie l'empâtement ?",
    "¿Qué significa el relieve?", "厚塗是什麼意思？",
])
def test_word_clarifications_use_the_contextual_model_path(text):
    assert asks_word_meaning(text)


@pytest.mark.parametrize("text", [
    "What does it mean?", "Que signifie cette œuvre ?", "Who painted it?",
    "What is this made of?", "I prefer simple words", "Use simple words please",
    "What is the meaning of this painting?", "這幅畫是什麼意思？",
])
def test_artwork_questions_and_style_preferences_are_not_word_definitions(text):
    assert not asks_word_meaning(text)


def test_vocabulary_question_does_not_learn_a_technical_style_preference():
    profile = SessionPersonalization()
    profile.complete_turn(preference_question_requested=True)
    profile.observe("Explain what the word technical means.")
    assert "technical" not in profile.explanation_styles
    assert not profile.awaiting_preference_answer


def test_plain_facts_cover_the_whole_offline_catalogue_in_all_public_languages():
    coverage = plain_catalog_languages()
    assert set(coverage) == scripted_catalog_artwork_ids()
    assert all(set(languages) == set(PUBLIC_SCRIPTED_LANGUAGES)
               for languages in coverage.values())
    for artwork_id, languages in coverage.items():
        for language in languages:
            facts = plain_facts(artwork_id, language)
            assert len(facts) == 8
            assert all(text.strip() for text in facts.values())
            facts["technique"] = "modified copy"
            assert plain_facts(artwork_id, language)["technique"] != "modified copy"


@pytest.mark.parametrize("language", PUBLIC_SCRIPTED_LANGUAGES)
@pytest.mark.parametrize("profile", ["early_child", "child", "simple_language"])
def test_plain_local_answers_do_not_reintroduce_known_jargon(language, profile):
    questions = {
        "en": "How was it made?", "fr": "Quelle technique ?",
        "es": "Como se hizo", "it": "Come e stato fatto", "zh": "怎麼做的",
    }
    for artwork_id in scripted_catalog_artwork_ids():
        answer = resolve_scripted_faq(
            questions[language], artwork_id=artwork_id,
            language=language, profile=profile,
        )
        assert answer is not None
        for jargon in ("impasto", "empâtement", "sfumato", "relief", "rilievo",
                       "empaste", "allegory", "allégorie", "glacis", "厚涂", "厚塗"):
            assert jargon not in answer.response.casefold()


def test_simple_accessibility_overlay_outranks_expert_faq_extras():
    answer = resolve_scripted_faq(
        "How was it made?", artwork_id="mona_lisa", language="en",
        profile="expert", accessibility=("simple_language", "audio_description"),
    )
    assert answer is not None
    assert "soft edges" in answer.response.lower()
    assert "poplar" not in answer.response
    assert "sfumato" not in answer.response
