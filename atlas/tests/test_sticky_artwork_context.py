"""Accepted offers and named subjects survive camera jitter without cloud calls."""

from __future__ import annotations

from pathlib import Path

import pytest

from atlas.app.dependency_container import Container
from atlas.audio.mock_tts import MockTTS
from atlas.audio.stt import TranscriptResult
from atlas.config.settings import PathsSettings, Settings
from atlas.dashboard.runtime_service import RuntimeService
from atlas.dialogue.conversation_memory import RECENT_TURNS, ConversationMemory
from atlas.dialogue.dialogue_engine import DialogueEngine
from atlas.dialogue.scripted_faq import _QUESTION_PHRASES
from atlas.vision.detector import ArtworkDetection
from tests.test_pipeline import _make_runner

MONA = "mona_lisa"
WAVE = "great_wave_off_kanagawa"
OFFER = "Voulez-vous découvrir La Grande Vague de Kanagawa ?"


def detection(artwork_id):
    return ArtworkDetection(
        artwork_id=artwork_id,
        label=artwork_id,
        confidence=0.95,
        stable=True,
        source="vision",
    )


@pytest.fixture
def workflow_service(tmp_path):
    root = Path(__file__).resolve().parents[1]
    container = Container(
        Settings(
            paths=PathsSettings(
                data_dir=tmp_path,
                content_packs_dir=root / "data/content_packs",
                chroma_dir=tmp_path / "chroma",
                sqlite_dir=tmp_path / "sqlite",
                logs_dir=tmp_path / "logs",
            )
        )
    )
    yield RuntimeService(container)
    container.close()


def memory_with_offer(answer=OFFER):
    memory = ConversationMemory()
    memory.focus("Parlons de la Joconde", MONA, 0)
    memory.remember("Explique ses couleurs", answer, MONA)
    return memory


@pytest.mark.parametrize(
    "offer,yes",
    [
        (OFFER, "Oui"),
        ("Would you like to learn about The Great Wave off Kanagawa?", "Yes"),
        ("¿Te gustaría descubrir La gran ola de Kanagawa?", "Sí"),
        ("Vuoi scoprire La grande onda di Kanagawa?", "Sì"),
        ("你想了解神奈川冲浪里吗？", "好的"),
        (
            "Je vous recommande La Grande Vague de Kanagawa. "
            "Voulez-vous en savoir plus ?",
            "Oui",
        ),
        (
            "You might enjoy The Great Wave off Kanagawa. Would you like to know more?",
            "Yes",
        ),
    ],
)
def test_spontaneous_offer_becomes_active_only_after_acceptance(offer, yes):
    memory = memory_with_offer(offer)
    assert memory.topic == MONA
    assert memory.pending_recommendation == WAVE
    focus = memory.focus(yes, MONA, 0)
    assert focus.artwork_id == WAVE and focus.accepted_recommendation
    assert memory.topic_locked


@pytest.mark.parametrize(
    "answer",
    [
        "La Grande Vague et la Joconde utilisent des compositions différentes.",
        "Voulez-vous comparer la Joconde et La Grande Vague ?",
        "Voulez-vous découvrir La Grande Vague ou La Nuit étoilée ?",
        "Voulez-vous découvrir une œuvre imaginaire inconnue ?",
        "La Grande Vague est une estampe. Quel point voulez-vous approfondir ?",
        "La Grande Vague est une estampe. Voulez-vous une autre blague ?",
    ],
)
def test_incidental_mentions_comparisons_and_ambiguous_offers_are_not_promoted(answer):
    memory = memory_with_offer(answer)
    assert memory.pending_recommendation is None
    assert memory.focus("Oui", MONA, 0).artwork_id == MONA


@pytest.mark.parametrize("question", ["Non merci", "Autre chose", "Raconte une blague"])
def test_rejection_or_interruption_consumes_offer_without_changing_subject(question):
    memory = memory_with_offer()
    assert memory.focus(question, MONA, 0).artwork_id == MONA
    assert memory.focus("Oui", MONA, 0).artwork_id == MONA


@pytest.mark.parametrize("accepted", [False, True])
def test_latest_spoken_subject_survives_twenty_followups_and_camera_changes(accepted):
    memory = memory_with_offer()
    memory.focus("Oui" if accepted else "Parlons de la Grande Vague", MONA, 0)
    for index in range(20):
        camera = [MONA, None, "starry_night", MONA][index % 4]
        focus = memory.focus("Et sa technique ?", camera, 0)
        assert focus.artwork_id == WAVE
        assert focus.live_artwork_id == camera
        memory.remember("Et sa technique ?", "Une réponse préparée.", WAVE)
    assert len(memory.recent) == RECENT_TURNS


@pytest.mark.parametrize(
    "question,force",
    [
        ("Qu'est-ce que je regarde ?", False),
        ("Que regardons-nous ?", False),
        ("Qu'est-ce qu'on regarde ?", False),
        ("What am I looking at?", False),
        ("", True),
    ],
)
def test_explicit_current_view_or_capture_reselects_camera_and_unlocks(question, force):
    memory = memory_with_offer()
    memory.focus("Oui", MONA, 0)
    focus = memory.focus(question, MONA, 0, force_camera=force)
    assert focus.artwork_id == MONA
    assert not memory.topic_locked
    assert memory.focus("Explain", "starry_night", 0).artwork_id == "starry_night"


def test_unavailable_camera_cannot_claim_a_remembered_work_is_currently_visible():
    memory = memory_with_offer()
    memory.focus("Oui", MONA, 0)
    focus = memory.focus("What am I looking at?", None, 0)
    assert focus.artwork_id is None and focus.live_artwork_id is None
    assert memory.focus("Tell me more about it", None, 0).artwork_id == WAVE


def test_visit_reset_clears_topic_lock_and_pending_offer():
    memory = memory_with_offer()
    memory.focus("Oui", MONA, 0)
    memory.remember("Explain", "Would you like to discover Sunflowers?", WAVE)
    memory.reset()
    assert not memory.topic_locked and memory.pending_recommendation is None
    assert memory.focus("Oui", None, 1).artwork_id is None
    assert memory.focus("Explain", MONA, 1).artwork_id == MONA


def test_new_named_work_replaces_locked_subject_and_implicit_this_stays_with_it():
    memory = memory_with_offer()
    memory.focus("Oui", MONA, 0)
    assert memory.focus("Parlons des Tournesols", MONA, 0).artwork_id == "sunflowers"
    assert (
        memory.focus("Who painted this?", "starry_night", 0).artwork_id == "sunflowers"
    )


class ProposalModel:
    def __init__(self):
        self.calls = 0

    def generate(self, _messages):
        self.calls += 1
        return "La Joconde utilise des tons doux. " + OFFER

    def generate_stream(self, messages):
        yield self.generate(messages)


def never_retrieve(*_args, **_kwargs):
    pytest.fail("Accepted prepared recommendations must not call retrieval")


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("entry", ["listen", "transcript"])
def test_generated_offer_then_yes_and_prepared_followups_stay_on_wave_locally(
    monkeypatch,
    streaming,
    entry,
):
    model = ProposalModel()
    engine = DialogueEngine(model)
    if streaming:
        engine.respond_stream(
            "Explique ses couleurs",
            [],
            on_sentence=lambda _: None,
            language="fr",
            artwork_id=MONA,
        )
    else:
        engine.respond("Explique ses couleurs", [], language="fr", artwork_id=MONA)
    runner = _make_runner(dialogue_engine=engine, retriever=never_retrieve)
    runner.set_preferred_language("fr")
    questions = (
        ["Oui"]
        + [_QUESTION_PHRASES[i]["fr"][0] for i in ["artist", "date", "technique"]]
        + ["Oui"]
    )
    for index, question in enumerate(questions):
        current = detection(MONA if index % 2 == 0 else "starry_night")
        if entry == "listen":
            monkeypatch.setattr(
                runner._stt,
                "listen",
                lambda value=question, **_kw: TranscriptResult(value, "fr"),
            )
            result = runner.run_once(detection_override=current)
        else:
            result = runner.respond_to_transcript(
                TranscriptResult(question, "fr"), detection=current
            )
        assert result.success and result.event == "scripted_faq"
        assert result.dialogue.response.endswith("?")
        assert engine._memory.topic == WAVE
        assert engine._memory.recent[-1].artwork_id == WAVE
        assert engine._memory.recent[-1].question == question
    assert model.calls == 1


def test_typed_offer_acceptance_uses_prepared_new_work_without_model_or_retrieval(
    workflow_service,
):
    service = workflow_service
    engine = service.container.dialogue_engine
    engine.prepare_turn("Parlons de la Joconde", MONA)
    engine.remember_local_response("Explique ses couleurs", OFFER, artwork_id=MONA)
    monkey_model = type("NoModel", (), {"generate": never_retrieve})()
    engine._llm = monkey_model
    service.container.retriever.retrieve = never_retrieve
    answer = service.ask("Oui", language="fr")
    assert answer["artwork_id"] == WAVE and answer["answer"].endswith("?")
    assert engine._memory.topic == WAVE


def test_complex_followup_retrieval_and_prompt_keep_discussion_separate_from_camera():
    class Model:
        def generate(self, messages):
            self.messages = messages
            return "The composition balances movement and stillness."

    model = Model()
    engine = DialogueEngine(model)
    engine.prepare_turn("Discuss Mona Lisa", MONA)
    engine.remember_local_response("Explain colour", OFFER, artwork_id=MONA)
    retrieved = []

    def retrieve(artwork_id, *_args):
        retrieved.append(artwork_id)
        return [{"text": "The composition balances movement and stillness."}]

    runner = _make_runner(dialogue_engine=engine, retriever=retrieve)
    runner.respond_to_transcript(
        TranscriptResult("Oui", "fr"), detection=detection(MONA)
    )
    answer = runner.respond_to_transcript(
        TranscriptResult("Explain the tension between movement and stillness"),
        detection=detection("starry_night"),
    )
    assert answer.success
    assert retrieved == [WAVE]
    prompt = model.messages[-1]["content"]
    assert "DISCUSSION ARTWORK: great_wave_off_kanagawa" in prompt
    assert "CURRENT ARTWORK: starry_night" in prompt


def test_camera_invitation_cannot_interrupt_a_locked_topic_but_manual_capture_can():
    class Speech(MockTTS):
        def __init__(self):
            super().__init__()
            self.spoken = []

        def speak(self, text, language="en"):
            self.spoken.append(text)
            return True

    engine = DialogueEngine(ProposalModel())
    engine.prepare_turn("Discuss the Great Wave off Kanagawa", MONA)
    tts = Speech()
    runner = _make_runner(dialogue_engine=engine, tts=tts)
    assert not runner.invite_about_artwork(detection(MONA))
    assert not tts.spoken
    engine.prepare_turn("", MONA, force_camera=True)
    assert runner.invite_about_artwork(detection(MONA))
    assert len(tts.spoken) == 1


def test_manual_capture_in_the_spoken_route_replaces_a_locked_discussion(monkeypatch):
    engine = DialogueEngine(ProposalModel())
    engine.prepare_turn("Discuss the Great Wave off Kanagawa", MONA)
    runner = _make_runner(dialogue_engine=engine)
    captured = ArtworkDetection(
        artwork_id=MONA,
        label="La Joconde",
        confidence=0.95,
        stable=True,
        source="manual_capture",
    )
    monkeypatch.setattr(
        runner._stt,
        "listen",
        lambda **_kwargs: TranscriptResult("Who painted it?"),
    )
    result = runner.run_once(detection_override=captured)
    assert result.success
    assert "Leonardo da Vinci" in result.dialogue.response
    assert engine._memory.topic == MONA
    assert not engine._memory.topic_locked


def test_local_chinese_invitation_preserves_main_traditional_output():
    engine = DialogueEngine(ProposalModel())
    focus = engine.prepare_turn("Who painted Mona Lisa?", MONA)
    result = engine.resolve_local_response(
        "这是什么？",
        artwork_id=MONA,
        language="zh",
        focus=focus,
    )
    assert result is not None
    assert "这" not in result.response
    assert result.response.endswith("？")


def test_visit_reset_during_spoken_input_cannot_answer_the_old_visitors_question(
    monkeypatch,
):
    engine = DialogueEngine(ProposalModel())
    runner = _make_runner(dialogue_engine=engine)

    def listen(**_kwargs):
        engine.reset_conversation()
        return TranscriptResult("Who painted the Mona Lisa?")

    monkeypatch.setattr(runner._stt, "listen", listen)
    result = runner.run_once(detection_override=detection(MONA))
    assert result.error == "session_cancelled"
    assert result.dialogue is None
    assert not engine._memory.recent
