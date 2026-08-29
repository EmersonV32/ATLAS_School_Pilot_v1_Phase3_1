"""Prompt-injection detection for visitor questions.

A questions-side guard: it flags attempts to manipulate ATLAS into ignoring
its rules, leaking prompts/secrets, or role-playing as another system. It is
deliberately a *first* line of defence — the system prompt rules and the
output validation in DialogueEngine still apply even if a pattern slips
through here.
"""
from __future__ import annotations

import re

_INJECTION_PATTERNS: list[str] = [
    r"ignore\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+(instructions?|rules?|prompts?)",
    r"reveal\s+(your\s+)?(system\s+)?prompt",
    r"show\s+(me\s+)?(your\s+)?(system\s+)?prompt",
    r"forget\s+(your|all|the)\s+(rules?|instructions?)",
    r"pretend\s+(you\s+are|to\s+be)\s+(not\s+atlas|another|a\s+different)",
    r"you\s+are\s+no\s+longer\s+atlas",
    r"make\s+up\s+(a\s+)?facts?",
    r"invent\s+(a\s+)?facts?",
    r"show\s+(me\s+)?(your\s+)?api\s*key",
    r"reveal\s+(your\s+)?api\s*key",
    r"bypass\s+(your\s+|the\s+)?(rules?|safety|filters?|restrictions?)",
    r"change\s+(your\s+)?safety\s+settings",
    r"disable\s+(your\s+)?(safety|filters?|rules?)",
    r"act\s+as\s+(another|a\s+different)\s+(ai|assistant|model|system)",
    r"jailbreak",
    r"developer\s+mode",
    r"(hidden|internal)\s+(rules?|instructions?|metadata|logs?)",
]

SAFE_RESPONSE = {
    "en": "I can only help with the artwork and the museum visit.",
    "fr": "Je peux seulement aider avec l'œuvre d'art et la visite du musée.",
    "es": "Solo puedo ayudar con la obra de arte y la visita al museo.",
    "it": "Posso aiutare solo con l'opera d'arte e la visita al museo.",
}


class PromptInjectionFilter:
    """Detects prompt-injection attempts in visitor questions."""

    def __init__(self) -> None:
        self._patterns = [
            re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS
        ]

    def is_injection(self, text: str) -> bool:
        return any(p.search(text) for p in self._patterns)

    def safe_response(self, language: str = "en") -> str:
        return SAFE_RESPONSE.get(language, SAFE_RESPONSE["en"])
