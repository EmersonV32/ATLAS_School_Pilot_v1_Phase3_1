"""Builds LLM prompt messages from retrieved context and visitor state."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DialogueContext:
    question: str
    artwork_chunks: list  # list of chunk objects or plain dicts
    visitor_age: int | None = None
    visitor_language: str = "en"
    max_context_chars: int = 3000


_SYSTEM_EN = (
    "You are ATLAS, a friendly and knowledgeable AI museum guide. "
    "Help visitors understand the artwork they are looking at. "
    "Answer ONLY from the provided context. "
    "If the context does not contain the answer, say so honestly — do not invent facts. "
    "Keep responses conversational, accurate, and under 150 words."
)

_SYSTEM_FR = (
    "Vous êtes ATLAS, un guide de musée IA amical et compétent. "
    "Aidez les visiteurs à comprendre l'œuvre d'art qu'ils regardent. "
    "Répondez UNIQUEMENT à partir du contexte fourni. "
    "Si le contexte ne contient pas la réponse, dites-le honnêtement — n'inventez pas de faits. "
    "Gardez les réponses conversationnelles, précises et en moins de 150 mots."
)

_LEVEL_HINTS = {
    "child": {
        "en": "\nSpeak simply and warmly, as if explaining to a curious child aged 8–11.",
        "fr": "\nParlez simplement et chaleureusement, comme si vous expliquiez à un enfant curieux de 8 à 11 ans.",
    },
    "teen": {
        "en": "\nSpeak clearly and engagingly, suitable for a teenager.",
        "fr": "\nParlez clairement et de manière engageante, adapté à un adolescent.",
    },
    "adult": {
        "en": "",
        "fr": "",
    },
    "senior": {
        "en": "\nSpeak clearly and at a measured, unhurried pace.",
        "fr": "\nParlez clairement et à un rythme mesuré et posé.",
    },
}


def _age_to_level(age: int | None) -> str:
    if age is None:
        return "adult"
    if age < 12:
        return "child"
    if age < 18:
        return "teen"
    if age >= 65:
        return "senior"
    return "adult"


def _extract_text(chunk) -> str:
    """Pull plain text out of a chunk regardless of whether it's a dict or object."""
    if isinstance(chunk, dict):
        return chunk.get("text", chunk.get("content", str(chunk)))
    return getattr(chunk, "text", getattr(chunk, "content", str(chunk)))


class PromptBuilder:
    """Assembles a [system, user] message list ready for any chat-style LLM."""

    def build(self, ctx: DialogueContext) -> list[dict]:
        lang = ctx.visitor_language
        system_text = _SYSTEM_FR if lang == "fr" else _SYSTEM_EN

        # Build context block, respecting char budget
        parts: list[str] = []
        total = 0
        for chunk in ctx.artwork_chunks:
            text = _extract_text(chunk).strip()
            if not text:
                continue
            if total + len(text) > ctx.max_context_chars:
                break
            parts.append(text)
            total += len(text)

        context_block = "\n\n---\n\n".join(parts) if parts else "(no artwork context available)"

        level = _age_to_level(ctx.visitor_age)
        level_hint = _LEVEL_HINTS.get(level, _LEVEL_HINTS["adult"]).get(lang, "")

        user_content = (
            f"CONTEXT:\n{context_block}\n\n"
            f"VISITOR QUESTION: {ctx.question}"
            f"{level_hint}"
        )

        return [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_content},
        ]
