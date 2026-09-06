"""Ephemeral, coarse visitor preferences for one ATLAS session.

This module deliberately stores only allow-listed art interests and explanation
styles. It never stores names, raw profiles, transcripts, or free-form notes.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

INTEREST_LABELS = {
    "stories": "stories and narratives",
    "technique": "artistic technique and materials",
    "symbols": "symbols and hidden meaning",
    "history": "historical context",
    "color-light": "colour and light",
    "people-society": "people and society",
}

STYLE_LABELS = {
    "concise": "brief answers",
    "detailed": "more depth and detail",
    "story-led": "story-led explanations",
    "technical": "technical art vocabulary",
    "simple": "simple language",
    "visual": "rich visual description",
    "slower": "a slower, reflective pace",
}

_INTEREST_TERMS = {
    "stories": (
        "story",
        "stories",
        "narrative",
        "myth",
        "recit",
        "relato",
        "storie",
        "racconto",
        "故事",
    ),
    "technique": (
        "technique",
        "materials",
        "brushwork",
        "tecnica",
        "materiales",
        "materiali",
        "技法",
        "材料",
    ),
    "symbols": (
        "symbol",
        "symbols",
        "symbole",
        "symboles",
        "simbolo",
        "simbolos",
        "simboli",
        "象徵",
        "象征",
    ),
    "history": (
        "history",
        "historical",
        "histoire",
        "historique",
        "historia",
        "historico",
        "storia",
        "storico",
        "歷史",
        "历史",
    ),
    "color-light": (
        "colour",
        "color",
        "light",
        "couleur",
        "lumiere",
        "luz",
        "colore",
        "luce",
        "色彩",
        "光線",
        "光线",
    ),
    "people-society": (
        "people",
        "society",
        "identity",
        "power",
        "personnes",
        "societe",
        "identite",
        "gente",
        "sociedad",
        "identidad",
        "persone",
        "societa",
        "identita",
        "人物",
        "社會",
        "社会",
    ),
}

_STYLE_TERMS = {
    "concise": (
        "short",
        "brief",
        "concise",
        "court",
        "bref",
        "corto",
        "breve",
        "簡短",
        "简短",
    ),
    "detailed": (
        "detail",
        "detailed",
        "depth",
        "approfondi",
        "detalle",
        "profundidad",
        "dettaglio",
        "approfondito",
        "詳細",
        "详细",
    ),
    "story-led": (
        "like a story",
        "comme une histoire",
        "como una historia",
        "come una storia",
        "像故事",
    ),
    "technical": (
        "technical",
        "terminology",
        "art terms",
        "vocabulaire technique",
        "tecnico",
        "terminos tecnicos",
        "termini tecnici",
        "技術",
        "技术",
        "術語",
        "术语",
    ),
    "simple": (
        "simple",
        "plain words",
        "facile",
        "sencillo",
        "semplice",
        "簡單",
        "简单",
    ),
    "visual": (
        "describe what you see",
        "visual description",
        "description visuelle",
        "descripcion visual",
        "descrizione visiva",
        "視覺描述",
        "视觉描述",
    ),
    "slower": (
        "slower",
        "slowly",
        "plus lent",
        "despacio",
        "piu lento",
        "慢一點",
        "慢一点",
    ),
}

_PREFERENCE_SIGNALS = (
    "i like",
    "i love",
    "i prefer",
    "i am interested",
    "i'm interested",
    "tell me",
    "explain",
    "j'aime",
    "je prefere",
    "m'interesse",
    "me gusta",
    "prefiero",
    "mi piace",
    "preferisco",
    "我喜歡",
    "我喜欢",
    "我想",
)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"\s+", " ", without_marks.casefold()).strip()


def _contains_term(text: str, term: str) -> bool:
    if any("\u3400" <= char <= "\u9fff" for char in term):
        return term in text
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) is not None


@dataclass
class SessionPersonalization:
    """Bounded preferences that exist only for the active visitor session."""

    interests: list[str] = field(default_factory=list)
    explanation_styles: list[str] = field(default_factory=list)
    completed_turns: int = 0
    awaiting_preference_answer: bool = False

    def reset(self) -> None:
        self.interests.clear()
        self.explanation_styles.clear()
        self.completed_turns = 0
        self.awaiting_preference_answer = False

    def configure(
        self,
        *,
        interests: list[str] | None = None,
        accessibility: list[str] | None = None,
        expertise: str | None = None,
    ) -> None:
        self.reset()
        for interest in interests or []:
            self._add(self.interests, interest, INTEREST_LABELS)
        for choice, style in {
            "audio_description": "visual",
            "simple_language": "simple",
            "slower_pace": "slower",
        }.items():
            if choice in (accessibility or []):
                self._add(self.explanation_styles, style, STYLE_LABELS)
        if expertise == "enthusiast":
            self._add(self.explanation_styles, "technical", STYLE_LABELS)

    @staticmethod
    def _add(target: list[str], value: str, allowlist: dict[str, str]) -> None:
        if value in allowlist and value not in target:
            target.append(value)

    def observe(self, utterance: str) -> None:
        """Extract allow-listed preferences locally without another LLM call."""
        normalized = _normalize(utterance)
        explicit = self.awaiting_preference_answer or any(
            signal in normalized for signal in _PREFERENCE_SIGNALS
        )
        self.awaiting_preference_answer = False
        if not explicit:
            return
        for interest, terms in _INTEREST_TERMS.items():
            if any(_contains_term(normalized, _normalize(term)) for term in terms):
                self._add(self.interests, interest, INTEREST_LABELS)
        for style, terms in _STYLE_TERMS.items():
            if any(_contains_term(normalized, _normalize(term)) for term in terms):
                self._add(self.explanation_styles, style, STYLE_LABELS)

    def should_ask_preference_question(self) -> bool:
        """Request no more than two useful preference questions per session."""
        if self.completed_turns == 0 and not self.explanation_styles:
            return True
        return self.completed_turns == 2 and len(self.interests) < 2

    def complete_turn(self, *, preference_question_requested: bool) -> None:
        self.completed_turns += 1
        self.awaiting_preference_answer = preference_question_requested

    def prompt_lines(self) -> tuple[str, str]:
        interests = ", ".join(INTEREST_LABELS[item] for item in self.interests)
        styles = ", ".join(STYLE_LABELS[item] for item in self.explanation_styles)
        return interests or "none stated", styles or "none stated"
