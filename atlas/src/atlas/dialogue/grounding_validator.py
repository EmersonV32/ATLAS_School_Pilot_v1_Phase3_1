"""Checks that a generated response has meaningful overlap with the retrieved context.

This is a heuristic guard. The production upgrade path is a cross-encoder
that scores (response, context) pairs directly. For now, answer-token coverage
with a configurable threshold is enough to catch totally unrelated answers.
"""
from __future__ import annotations

import re
import unicodedata


def _tokens(text: str) -> set[str]:
    """Accent-insensitive alphabetic tokens of four or more characters."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return set(re.findall(r"\b[a-z]{4,}\b", ascii_text.lower()))


class GroundingValidator:
    """
    Validates that a response is grounded in the retrieved context.

    Returns (is_grounded: bool, reason: str).
    """

    def __init__(self, min_overlap: float = 0.05) -> None:
        # Five percent is intentionally permissive because grounded answers
        # can paraphrase the source and use a different visitor language.
        self.min_overlap = min_overlap

    def validate(
        self,
        response: str,
        context_chunks: list,
    ) -> tuple[bool, str]:
        # Mock responses are always considered grounded for test purposes
        if response.startswith("[MOCK]"):
            return True, "mock_response"

        stripped = response.strip()
        if len(stripped) < 15:
            return False, "response_too_short"

        # Imported here to avoid a module-level circular dependency.
        from atlas.dialogue.prompt_builder import _extract_text

        context_text = " ".join(_extract_text(c) for c in context_chunks)
        ctx_tokens = _tokens(context_text)

        if not ctx_tokens:
            # Nothing to check against — allow response through
            return True, "no_context_available"

        resp_tokens = _tokens(stripped)
        if not resp_tokens:
            return False, "response_no_meaningful_tokens"

        intersection = ctx_tokens & resp_tokens
        response_coverage = len(intersection) / len(resp_tokens)

        if response_coverage < self.min_overlap:
            return False, f"low_overlap:{response_coverage:.3f}"

        return True, f"ok:{response_coverage:.3f}"
