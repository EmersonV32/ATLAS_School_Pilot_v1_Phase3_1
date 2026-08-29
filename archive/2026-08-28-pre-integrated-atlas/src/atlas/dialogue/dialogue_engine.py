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

import json
import logging
import re
from dataclasses import dataclass, field

from atlas.dialogue.prompt_builder import PromptBuilder, DialogueContext, _extract_chunk_id
from atlas.dialogue.grounding_validator import GroundingValidator
from atlas.dialogue.safety_filter import SafetyFilter
from atlas.safety.prompt_injection_filter import PromptInjectionFilter

logger = logging.getLogger(__name__)

# Spoken refusal used when an answer is not grounded in verified context.
UNGROUNDED_FALLBACK = {
    "en": (
        "I don't have that detail verified in my guide yet, but I can tell "
        "you what is confirmed about this artwork."
    ),
    "fr": (
        "Je n'ai pas encore cette information vérifiée dans mon guide, mais "
        "je peux expliquer ce qui est confirmé sur cette œuvre."
    ),
}


@dataclass
class DialogueResult:
    response: str
    language: str
    grounded: bool
    grounding_reason: str
    filtered: bool
    error: str | None = None
    used_chunk_ids: list[str] = field(default_factory=list)
    confidence: str = "medium"  # high | medium | low
    fallback_used: bool = False


def _parse_structured(raw: str) -> dict | None:
    """Parse the LLM JSON contract if present; None means plain text.

    Accepts bare JSON or JSON inside a ```json fence. Requires a non-empty
    spoken_answer to count as structured output.
    """
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    spoken = data.get("spoken_answer")
    if not isinstance(spoken, str) or not spoken.strip():
        return None
    return data


class DialogueEngine:
    """
    Orchestrates prompt building, LLM generation, grounding validation,
    and safety filtering for a single visitor question.

    The llm_client is injected — pass MockLLMClient for dev/test,
    GeminiClient for device/demo modes.
    """

    def __init__(self, llm_client, expect_json: bool = False) -> None:
        self._llm = llm_client
        self._expect_json = expect_json  # True for real LLMs (Gemini)
        self._prompt_builder = PromptBuilder()
        self._validator = GroundingValidator()
        self._safety = SafetyFilter()
        self._injection = PromptInjectionFilter()

    def respond(
        self,
        question: str,
        artwork_chunks: list,
        visitor_age: int | None = None,
        language: str = "en",
        profile: str | None = None,
    ) -> DialogueResult:
        # 0. Prompt-injection guard — refuse before any LLM call.
        if self._injection.is_injection(question):
            logger.warning("Prompt injection detected — refusing safely.")
            return DialogueResult(
                response=self._injection.safe_response(language),
                language=language,
                grounded=True,
                grounding_reason="injection_refused",
                filtered=True,
                fallback_used=True,
                confidence="high",
            )

        # 1. Build prompt
        ctx = DialogueContext(
            question=question,
            artwork_chunks=artwork_chunks,
            visitor_age=visitor_age,
            visitor_language=language,
            profile=profile,
        )
        messages = self._prompt_builder.build(ctx, json_output=self._expect_json)

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
                fallback_used=True,
                confidence="low",
            )

        # 2b. Parse the structured JSON contract when present. Plain text
        # (e.g. from MockLLMClient) is used as the spoken answer directly.
        spoken = raw_response
        used_chunk_ids: list[str] = []
        confidence = "medium"
        unsupported_claims: list = []
        structured = _parse_structured(raw_response)
        if structured is not None:
            spoken = structured["spoken_answer"].strip()
            confidence = str(structured.get("confidence", "medium"))
            claims = structured.get("unsupported_claims")
            unsupported_claims = claims if isinstance(claims, list) else []
            # used_chunk_ids must refer to chunks we actually retrieved.
            known_ids = {
                cid for cid in (_extract_chunk_id(c) for c in artwork_chunks) if cid
            }
            raw_ids = structured.get("used_chunk_ids") or []
            if isinstance(raw_ids, list):
                used_chunk_ids = [str(i) for i in raw_ids if str(i) in known_ids]
                invalid = [str(i) for i in raw_ids if str(i) not in known_ids]
                if invalid:
                    logger.warning("LLM cited unknown chunk ids: %s", invalid)

        # 3. Grounding check (+ unsupported-claims check from the contract).
        is_grounded, grounding_reason = self._validator.validate(spoken, artwork_chunks)
        if unsupported_claims:
            is_grounded = False
            grounding_reason = "unsupported_claims"
        fallback_used = bool(structured and structured.get("fallback_used"))
        if not is_grounded:
            logger.warning(
                "Grounding check failed (%s) — refusing with safe fallback.",
                grounding_reason,
            )
            spoken = UNGROUNDED_FALLBACK.get(language, UNGROUNDED_FALLBACK["en"])
            fallback_used = True
            confidence = "low"

        # 4. Safety filter (always speaks last).
        final_response, was_filtered = self._safety.filter(spoken, language)
        if was_filtered:
            logger.warning("Response was blocked by safety filter.")

        return DialogueResult(
            response=final_response,
            language=language,
            grounded=is_grounded,
            grounding_reason=grounding_reason,
            filtered=was_filtered,
            used_chunk_ids=used_chunk_ids,
            confidence=confidence,
            fallback_used=fallback_used,
        )
