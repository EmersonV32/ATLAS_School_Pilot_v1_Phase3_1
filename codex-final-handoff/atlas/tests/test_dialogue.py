"""Tests for Phase 3 dialogue components.

Run from the atlas project root with:
    python -m pytest tests/test_dialogue.py -v
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk(text: str) -> dict:
    return {"text": text}


_STARRY_NIGHT_CHUNKS = [
    _chunk(
        "The Starry Night is an oil-on-canvas painting by Dutch Post-Impressionist "
        "artist Vincent van Gogh. Painted in June 1889, it depicts the view from the "
        "east-facing window of his asylum room at Saint-Paul-de-Mausole, near "
        "Saint-Rémy-de-Provence, France."
    ),
    _chunk(
        "The painting is dominated by a swirling night sky filled with luminous stars "
        "and a crescent moon over a village. It is one of the most recognised works in "
        "Western art and has been in the permanent collection of the Museum of Modern "
        "Art in New York City since 1941."
    ),
]


# ---------------------------------------------------------------------------
# MockLLMClient
# ---------------------------------------------------------------------------


class TestMockLLMClient:
    def test_returns_string(self):
        from atlas.dialogue.mock_llm_client import MockLLMClient

        client = MockLLMClient()
        messages = [{"role": "user", "content": "Who painted this?"}]
        result = client.generate(messages)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_deterministic(self):
        from atlas.dialogue.mock_llm_client import MockLLMClient

        client = MockLLMClient()
        messages = [{"role": "user", "content": "Who painted this?"}]
        assert client.generate(messages) == client.generate(messages)

    def test_different_questions_can_differ(self):
        from atlas.dialogue.mock_llm_client import MockLLMClient

        client = MockLLMClient()
        r1 = client.generate([{"role": "user", "content": "question one"}])
        r2 = client.generate([{"role": "user", "content": "question two"}])
        # They may collide by hash — just check both are non-empty strings
        assert isinstance(r1, str) and isinstance(r2, str)

    def test_starts_with_mock_tag(self):
        from atlas.dialogue.mock_llm_client import MockLLMClient

        result = MockLLMClient().generate([{"role": "user", "content": "test"}])
        assert result.startswith("[MOCK]")


# ---------------------------------------------------------------------------
# PromptBuilder
# ---------------------------------------------------------------------------


class TestPromptBuilder:
    def test_returns_two_messages(self):
        from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder

        ctx = DialogueContext(
            question="Who painted this?", artwork_chunks=_STARRY_NIGHT_CHUNKS
        )
        messages = PromptBuilder().build(ctx)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_user_message_contains_question(self):
        from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder

        ctx = DialogueContext(
            question="When was this painted?", artwork_chunks=_STARRY_NIGHT_CHUNKS
        )
        messages = PromptBuilder().build(ctx)
        assert "When was this painted?" in messages[1]["content"]

    def test_user_message_contains_context(self):
        from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder

        ctx = DialogueContext(
            question="Tell me more.", artwork_chunks=_STARRY_NIGHT_CHUNKS
        )
        messages = PromptBuilder().build(ctx)
        assert "van Gogh" in messages[1]["content"]

    def test_french_system_prompt(self):
        from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder

        ctx = DialogueContext(
            question="Qui a peint ceci?",
            artwork_chunks=_STARRY_NIGHT_CHUNKS,
            visitor_language="fr",
        )
        messages = PromptBuilder().build(ctx)
        assert "You are ATLAS" in messages[0]["content"]
        assert "<selected_language>fr</selected_language>" in messages[1]["content"]

    def test_system_prompt_allows_general_knowledge_when_rag_is_empty(self):
        from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder

        messages = PromptBuilder().build(
            DialogueContext(question="What is the capital of Japan?", artwork_chunks=[])
        )
        system = messages[0]["content"]
        assert "well-established general knowledge" in system
        assert "general knowledge to guess an artwork's identity" in system
        assert "Answer ONLY from the verified context" not in system

    def test_json_output_attaches_provider_schema(self):
        from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder

        messages = PromptBuilder().build(
            DialogueContext(question="Who painted this?", artwork_chunks=[]),
            json_output=True,
        )
        response_format = messages[0]["response_format"]
        assert response_format["mime_type"] == "application/json"
        assert response_format["schema"]["required"] == [
            "spoken_answer",
            "used_chunk_ids",
            "confidence",
            "unsupported_claims",
            "fallback_used",
        ]

    def test_system_prompt_repairs_only_clear_speech_errors(self):
        from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder

        ctx = DialogueContext(
            question="Qui appelle la Joconde?",
            artwork_chunks=_STARRY_NIGHT_CHUNKS,
            visitor_language="fr",
        )
        system = PromptBuilder().build(ctx)[0]["content"]
        assert "homophone" in system
        assert "ask one short clarifying question" in system
        assert "Qui a peint la Joconde" in system
        user = PromptBuilder().build(ctx)[1]["content"]
        assert "LIKELY INTENDED QUESTION AFTER SPEECH REPAIR" in user
        assert "Qui a peint la Joconde ?" in user

    def test_child_age_adds_hint(self):
        from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder

        ctx = DialogueContext(
            question="What is this?",
            artwork_chunks=_STARRY_NIGHT_CHUNKS,
            visitor_age=9,
        )
        messages = PromptBuilder().build(ctx)
        assert (
            "child" in messages[1]["content"].lower() or "8" in messages[1]["content"]
        )

    def test_empty_chunks_handled(self):
        from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder

        ctx = DialogueContext(question="Tell me something.", artwork_chunks=[])
        messages = PromptBuilder().build(ctx)
        assert "no artwork context" in messages[1]["content"].lower()


# ---------------------------------------------------------------------------
# GroundingValidator
# ---------------------------------------------------------------------------


class TestGroundingValidator:
    def test_mock_response_always_passes(self):
        from atlas.dialogue.grounding_validator import GroundingValidator

        v = GroundingValidator()
        ok, reason = v.validate("[MOCK] Some response.", _STARRY_NIGHT_CHUNKS)
        assert ok is True
        assert reason == "mock_response"

    def test_short_response_fails(self):
        from atlas.dialogue.grounding_validator import GroundingValidator

        v = GroundingValidator()
        ok, reason = v.validate("Yes.", _STARRY_NIGHT_CHUNKS)
        assert ok is False
        assert reason == "response_too_short"

    def test_on_topic_response_passes(self):
        from atlas.dialogue.grounding_validator import GroundingValidator

        v = GroundingValidator()
        response = (
            "Vincent van Gogh painted The Starry Night in 1889 while he was "
            "staying at the Saint-Paul-de-Mausole asylum in France."
        )
        ok, reason = v.validate(response, _STARRY_NIGHT_CHUNKS)
        assert ok is True
        assert reason.startswith("ok:")

    def test_completely_off_topic_fails(self):
        from atlas.dialogue.grounding_validator import GroundingValidator

        v = GroundingValidator()
        response = (
            "Quantum computing uses superposition and entanglement to perform "
            "calculations that classical computers cannot efficiently simulate."
        )
        ok, reason = v.validate(response, _STARRY_NIGHT_CHUNKS)
        assert ok is False

    def test_french_paraphrase_passes_with_large_context(self):
        from atlas.dialogue.grounding_validator import GroundingValidator

        context = _STARRY_NIGHT_CHUNKS + [
            {
                "text": "La Joconde, aussi appel\u00e9e Mona Lisa, a \u00e9t\u00e9 "
                "peinte par L\u00e9onard de Vinci."
            }
        ] * 20
        response = "La Joconde a \u00e9t\u00e9 peinte par L\u00e9onard de Vinci."
        ok, reason = GroundingValidator().validate(response, context)
        assert ok is True
        assert reason.startswith("ok:")

    def test_no_context_passes_through(self):
        from atlas.dialogue.grounding_validator import GroundingValidator

        v = GroundingValidator()
        ok, reason = v.validate("This painting is remarkable.", [])
        assert ok is True
        assert reason == "no_context_available"


# ---------------------------------------------------------------------------
# SafetyFilter
# ---------------------------------------------------------------------------


class TestSafetyFilter:
    def test_clean_response_passes(self):
        from atlas.dialogue.safety_filter import SafetyFilter

        f = SafetyFilter()
        result, was_filtered = f.filter("This painting uses vibrant blues and yellows.")
        assert was_filtered is False
        assert "painting" in result

    def test_violence_blocked(self):
        from atlas.dialogue.safety_filter import SafetyFilter

        f = SafetyFilter()
        result, was_filtered = f.filter("This depicts extreme violence and murder.")
        assert was_filtered is True

    def test_french_fallback_used(self):
        from atlas.dialogue.safety_filter import SafetyFilter

        f = SafetyFilter()
        result, was_filtered = f.filter("This depicts violence.", language="fr")
        assert was_filtered is True
        assert "répondre" in result  # French fallback text

    def test_art_nude_allowed(self):
        from atlas.dialogue.safety_filter import SafetyFilter

        f = SafetyFilter()
        result, was_filtered = f.filter(
            "This is a nude figure commonly found in Renaissance painting."
        )
        assert was_filtered is False


# ---------------------------------------------------------------------------
# DialogueEngine (integration)
# ---------------------------------------------------------------------------


class TestDialogueEngine:
    def _engine(self):
        from atlas.dialogue.dialogue_engine import DialogueEngine
        from atlas.dialogue.mock_llm_client import MockLLMClient

        return DialogueEngine(llm_client=MockLLMClient())

    def test_basic_response_returned(self):
        engine = self._engine()
        result = engine.respond(
            question="Who painted this?",
            artwork_chunks=_STARRY_NIGHT_CHUNKS,
        )
        assert isinstance(result.response, str)
        assert len(result.response) > 0

    def test_result_has_expected_fields(self):
        engine = self._engine()
        result = engine.respond(
            question="When was it painted?",
            artwork_chunks=_STARRY_NIGHT_CHUNKS,
        )
        assert hasattr(result, "response")
        assert hasattr(result, "grounded")
        assert hasattr(result, "filtered")
        assert hasattr(result, "language")
        assert hasattr(result, "grounding_reason")

    def test_mock_response_grounded_true(self):
        engine = self._engine()
        result = engine.respond(
            question="Describe this painting.",
            artwork_chunks=_STARRY_NIGHT_CHUNKS,
        )
        assert result.grounded is True

    def test_french_language_propagated(self):
        engine = self._engine()
        result = engine.respond(
            question="Qui a peint ceci?",
            artwork_chunks=_STARRY_NIGHT_CHUNKS,
            language="fr",
        )
        assert result.language == "fr"

    def test_empty_chunks_still_returns_response(self):
        engine = self._engine()
        result = engine.respond(
            question="What is this?",
            artwork_chunks=[],
        )
        assert isinstance(result.response, str)

    def test_child_visitor(self):
        engine = self._engine()
        result = engine.respond(
            question="What is the night sky?",
            artwork_chunks=_STARRY_NIGHT_CHUNKS,
            visitor_age=9,
        )
        assert result.error is None


def test_prompt_includes_only_immediate_prior_exchange_for_clear_followups():
    from atlas.dialogue.prompt_builder import DialogueContext, PromptBuilder

    messages = PromptBuilder().build(
        DialogueContext(
            question="What artworks did you painted?",
            artwork_chunks=[],
            recent_turn=(
                "Visitor: Who is Leonardo da Vinci?\n"
                "ATLAS: He was a Renaissance artist."
            ),
        )
    )
    assert "IMMEDIATE PRIOR EXCHANGE" in messages[1]["content"]
    assert "Leonardo da Vinci" in messages[1]["content"]
    assert "What artworks did he paint" in messages[0]["content"]
