"""DialogueEngine: the main orchestrator for Phase 3.

Pipeline:
    question + chunks
        → PromptBuilder         (assemble messages)
        → LLM client            (MockLLMClient in dev, GeminiClient in device/demo)
        → GroundingValidator    (token-overlap heuristic)
        → SafetyFilter          (block inappropriate content)
        → DialogueResult

Usage example (dev mode):
    from atlas.dialogue.mock_llm_client import MockLLMClient
    from atlas.dialogue.dialogue_engine import DialogueEngine

    engine = DialogueEngine(llm_client=MockLLMClient())
    result = engine.respond(
        question="Who painted this?",
        artwork_chunks=[{"text": "The Starry Night was painted by Vincent van Gogh in 1889."}],
        language="en",
    )
    print(result.response)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from atlas.dialogue.prompt_builder import PromptBuilder, DialogueContext
from atlas.dialogue.grounding_validator import GroundingValidator
from atlas.dialogue.safety_filter import SafetyFilter

logger = logging.getLogger(__name__)


@dataclass
class DialogueResult:
    response: str
    language: str
    grounded: bool
    grounding_reason: str
    filtered: bool
    error: str | None = None


class DialogueEngine:
    """
    Orchestrates prompt building, LLM generation, grounding validation,
    and safety filtering for a single visitor question.

    The llm_client is injected — pass MockLLMClient for dev/test,
    GeminiClient for device/demo modes.
    """

    def __init__(self, llm_client) -> None:
        self._llm = llm_client
        self._prompt_builder = PromptBuilder()
        self._validator = GroundingValidator()
        self._safety = SafetyFilter()

    def respond(
        self,
        question: str,
        artwork_chunks: list,
        visitor_age: int | None = None,
        language: str = "en",
    ) -> DialogueResult:
        # 1. Build prompt
        ctx = DialogueContext(
            question=question,
            artwork_chunks=artwork_chunks,
            visitor_age=visitor_age,
            visitor_language=language,
        )
        messages = self._prompt_builder.build(ctx)

        # 2. Call LLM
        raw_response: str
        try:
            raw_response = self._llm.generate(messages)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("LLM generation failed: %s", exc)
            fallback = (
                "Je suis désolé, je ne peux pas répondre en ce moment."
                if language == "fr"
                else "I'm sorry, I can't generate a response right now."
            )
            return DialogueResult(
                response=fallback,
                language=language,
                grounded=False,
                grounding_reason="llm_error",
                filtered=False,
                error=str(exc),
            )

        # 3. Grounding check
        is_grounded, grounding_reason = self._validator.validate(raw_response, artwork_chunks)
        if not is_grounded:
            logger.warning(
                "Grounding check failed (%s) — response may not be based on context.",
                grounding_reason,
            )

        # 4. Safety filter
        final_response, was_filtered = self._safety.filter(raw_response, language)
        if was_filtered:
            logger.warning("Response was blocked by safety filter.")

        return DialogueResult(
            response=final_response,
            language=language,
            grounded=is_grounded,
            grounding_reason=grounding_reason,
            filtered=was_filtered,
        )
