"""Keep generated self-introductions out of ordinary museum answers."""

from __future__ import annotations

import re

_IDENTITY_PREFIX = re.compile(
    r"^\s*(?:(?:i(?:\s+am|['’]m)|my\s+name\s+is)\s+atlas|"
    r"je\s+(?:suis|m['’]appelle)\s+atlas|"
    r"je\s+me\s+pr[ée]sente\s*[,:\-–—]?\s*"
    r"(?:(?:je\s+suis|je\s+m['’]appelle)\s+)?atlas)\b",
    re.IGNORECASE,
)
_GREETING_PREFIX = re.compile(
    r"^\s*(?:hello|hi|hey|bonjour|salut|bonsoir|je\s+me\s+pr[ée]sente)"
    r"(?:[.!,:;]\s*|\s*$)",
    re.IGNORECASE,
)
_SENTENCE_END = re.compile(r"[.!?;](?:\s+|$)")


def _without_leading_introduction(text: str) -> str:
    remaining = text.strip()
    while remaining:
        identity = _IDENTITY_PREFIX.match(remaining)
        if identity:
            ending = _SENTENCE_END.search(remaining, identity.end())
            remaining = remaining[ending.end():].strip() if ending else ""
            continue
        greeting = _GREETING_PREFIX.match(remaining)
        if greeting:
            remaining = remaining[greeting.end():].strip()
            continue
        break
    return remaining


def without_model_introduction(text: str) -> str:
    """Remove English/French greetings and ATLAS sentence introductions.

    This applies only to model output. The local wake greeting deliberately
    bypasses it. Third-person references, quotations, and artwork names remain.
    """
    stripped = text.strip()
    sentences = re.split(r"(?<=[.!?])\s+", stripped)
    cleaned = [_without_leading_introduction(sentence) for sentence in sentences]
    return stripped if sentences == cleaned else " ".join(filter(None, cleaned))


def introduction_fallback(language: str) -> str:
    """Invite an artwork question when a model supplied only an introduction."""
    return {
        "en": "Which artwork would you like to explore?",
        "fr": "Quelle œuvre souhaitez-vous explorer ?",
        "es": "¿Qué obra te gustaría explorar?",
        "it": "Quale opera vuoi esplorare?",
        "zh": "您想探索哪一件藝術品？",
    }.get(language, "Which artwork would you like to explore?")
