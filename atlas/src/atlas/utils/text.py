"""Light text utilities.

`clean_asr` performs *light* cleanup only. It must never change meaning;
the raw transcript is always preserved separately for logs.
"""

from __future__ import annotations

import re

_WS = re.compile(r"\s+")


def normalize_whitespace(text: str) -> str:
    return _WS.sub(" ", text).strip()


def clean_asr(text: str) -> str:
    """Light ASR cleanup: collapse whitespace, fix spacing before punctuation.

    Deliberately conservative. No spelling correction, no word substitution.
    """
    text = normalize_whitespace(text)
    text = re.sub(r"\s+([?.!,;:])", r"\1", text)
    return text


def truncate(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "\u2026"


def looks_like_pronoun_only(text: str) -> bool:
    """Heuristic: query is vague (pronoun-led) and may need the artwork title.

    Used by the query rewriter (Phase 2) to decide whether to inject the
    detected artwork title. Conservative on purpose.
    """
    lowered = normalize_whitespace(text).lower()
    vague_starts = (
        "what is this",
        "what's this",
        "who made it",
        "who made this",
        "tell me about it",
        "what is it",
        "qu'est-ce que c'est",
        "c'est quoi",
        "qui a fait",
    )
    return any(lowered.startswith(s) for s in vague_starts)
