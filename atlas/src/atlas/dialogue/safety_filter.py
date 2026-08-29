"""Content safety filter for museum guide context.

Catches responses with clearly inappropriate content and replaces them with a
safe fallback. Intentionally conservative — museum audiences include children.

Note: "nude" and "naked" are allowed when followed by art/sculpture/painting
terminology, since those are legitimate art-history terms (e.g. "nude figure
in Renaissance painting").
"""
from __future__ import annotations

import re

_BLOCKED: list[str] = [
    r"\b(violence|violent|weapon|weapons|kill|kills|murder|bomb|terrorist|terrorism)\b",
    r"\b(sexually explicit|pornograph)",
    r"\bnude(?!\s+(figure|sculpture|painting|artwork|study|form|model))\b",
    r"\bnaked(?!\s+(truth|eye|figure|form))\b",
]

_FALLBACK = {
    "en": (
        "I'm not able to answer that in this context. "
        "Feel free to ask me anything about the artwork you're viewing."
    ),
    "fr": (
        "Je ne suis pas en mesure de répondre à cela dans ce contexte. "
        "N'hésitez pas à me poser des questions sur l'œuvre que vous regardez."
    ),
    "es": (
        "No puedo responder a eso en este contexto. Puedes hacerme preguntas "
        "sobre la obra que estás mirando."
    ),
    "it": (
        "Non posso rispondere a questo in questo contesto. Puoi farmi domande "
        "sull'opera che stai guardando."
    ),
}


class SafetyFilter:
    """Returns (safe_response, was_filtered: bool)."""

    def __init__(self) -> None:
        self._patterns = [
            re.compile(p, re.IGNORECASE) for p in _BLOCKED
        ]

    def filter(self, response: str, language: str = "en") -> tuple[str, bool]:
        for pattern in self._patterns:
            if pattern.search(response):
                fallback = _FALLBACK.get(language, _FALLBACK["en"])
                return fallback, True
        return response, False
