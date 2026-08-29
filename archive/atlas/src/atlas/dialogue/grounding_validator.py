"""Checks that a generated response has meaningful overlap with the retrieved context.

This is a heuristic guard — the production upgrade path is a cross-encoder
reranker that scores (response, context) pairs directly. For now, token-overlap
with a configurable threshold is good enough to catch total hallucination.
"""
from __future__ import annotations

import re


def _tokens(text: str) -> set[str]:
    """Lowercase alphabetic tokens of 4+ characters."""
    return set(re.findall(r"\b[a-z]{4,}\b", text.lower()))


class GroundingValidator:
    """
    Validates that a response is grounded in the retrieved context.

    Returns (is_grounded: bool, reason: str).
    """

    def __init__(self, min_overlap: float = 0.05) -> None:
        # Jaccard overlap threshold — 5% is intentionally permissive;
        # responses can be paraphrases without sharing many exact tokens.
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

        # Build context token set
        from atlas.dialogue.prompt_builder import _extract_text  # avoid circular at module level

        context_text = " ".join(_extract_text(c) for c in context_chunks)
        ctx_tokens = _tokens(context_text)

        if not ctx_tokens:
            # Nothing to check against — allow response through
            return True, "no_context_available"

        resp_tokens = _tokens(stripped)
        if not resp_tokens:
            return False, "response_no_meaningful_tokens"

        union = ctx_tokens | resp_tokens
        intersection = ctx_tokens & resp_tokens
        jaccard = len(intersection) / len(union)

        if jaccard < self.min_overlap:
            return False, f"low_overlap:{jaccard:.3f}"

        return True, f"ok:{jaccard:.3f}"
