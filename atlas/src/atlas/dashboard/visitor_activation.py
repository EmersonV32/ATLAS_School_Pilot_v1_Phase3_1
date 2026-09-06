"""Local-only visitor wake phrase and greeting helpers."""

from __future__ import annotations

import re
import unicodedata

_WAKE_PHRASES = {
    "en": ("hello atlas", "hi atlas"),
    "fr": ("bonjour atlas", "salut atlas"),
    "es": ("hola atlas",),
    "it": ("ciao atlas", "salve atlas"),
    "zh": ("你好 atlas", "你好atlas", "哈囉 atlas", "哈啰 atlas"),
}

_GREETINGS = {
    "en": ("Hi {name}, I'm ATLAS.", "Hello, I'm ATLAS."),
    "fr": ("Bonjour {name}, je suis ATLAS.", "Bonjour, je suis ATLAS."),
    "es": ("Hola {name}, soy ATLAS.", "Hola, soy ATLAS."),
    "it": ("Ciao {name}, sono ATLAS.", "Ciao, sono ATLAS."),
    "zh": ("你好，{name}，我是 ATLAS。", "你好，我是 ATLAS。"),
}

_INVITATIONS = {
    "en": "Look at an artwork and ask me anything about it.",
    "fr": "Regardez une œuvre et posez-moi toutes vos questions.",
    "es": "Mira una obra y pregúntame lo que quieras sobre ella.",
    "it": "Guarda un'opera e chiedimi quello che vuoi.",
    "zh": "請看向一件藝術品，然後問我任何問題。",
}


def _language_root(language: str) -> str:
    root = str(language or "en").casefold().split("-", 1)[0]
    return root if root in _WAKE_PHRASES else "en"


def _normalize_phrase(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = re.sub(r"[^\w\u3400-\u9fff]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def wake_phrase_matches(transcript: str, language: str) -> bool:
    """Match a selected-language wake phrase without an LLM or network call."""
    normalized = _normalize_phrase(transcript)
    for phrase in _WAKE_PHRASES[_language_root(language)]:
        candidate = _normalize_phrase(phrase)
        if normalized == candidate or normalized.startswith(candidate + " "):
            return True
    return False


def clean_greeting_name(value: str | None) -> str | None:
    """Return a short human name or reject unsafe/unexpected characters."""
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    if len(cleaned) > 40:
        raise ValueError("greeting name must be 40 characters or fewer")
    allowed_punctuation = {" ", "-", "'", "’"}
    if not all(
        unicodedata.category(char).startswith(("L", "M")) or char in allowed_punctuation
        for char in cleaned
    ):
        raise ValueError("greeting name contains unsupported characters")
    return cleaned


def local_greeting(language: str, name: str | None = None) -> str:
    """Build the one-time greeting that must stay on the local Jetson."""
    root = _language_root(language)
    named, anonymous = _GREETINGS[root]
    opening = named.format(name=name) if name else anonymous
    return f"{opening} {_INVITATIONS[root]}"
