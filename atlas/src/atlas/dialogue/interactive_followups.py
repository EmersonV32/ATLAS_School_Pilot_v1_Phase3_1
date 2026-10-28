"""Small, truthful invitations for prepared answers; no model or network call."""

from __future__ import annotations

_TOPICS = {
    "en": {
        "artist": "the artist",
        "technique": "how it was made",
        "detail": "a detail to notice",
        "fun_fact": "a surprising fact about it",
        "meaning": "what it means",
    },
    "fr": {
        "artist": "son artiste",
        "technique": "la technique utilisée",
        "detail": "un détail à observer",
        "fun_fact": "un fait surprenant sur cette œuvre",
        "meaning": "le sens de cette œuvre",
    },
    "es": {
        "artist": "el artista",
        "technique": "cómo se hizo",
        "detail": "un detalle de la obra",
        "fun_fact": "un dato sorprendente de la obra",
        "meaning": "su significado",
    },
    "it": {
        "artist": "l'artista",
        "technique": "come è stata realizzata",
        "detail": "un dettaglio dell'opera",
        "fun_fact": "una curiosità sull'opera",
        "meaning": "il suo significato",
    },
    "zh": {
        "artist": "創作者",
        "technique": "製作方法",
        "detail": "值得注意的細節",
        "fun_fact": "這件作品的一個有趣知識",
        "meaning": "作品的含義",
    },
}
_FORMS = {
    "en": (
        "Would you like to explore {topic}?",
        "Are you curious about {topic}?",
        "Shall we take a closer look at {topic}?",
    ),
    "fr": (
        "Voulez-vous en savoir plus sur {topic} ?",
        "Est-ce que vous aimeriez explorer {topic} ?",
        "Ça vous intéresserait de découvrir {topic} ?",
    ),
    "es": (
        "¿Quieres saber más sobre {topic}?",
        "¿Te interesa {topic}?",
        "¿Exploramos {topic} con más detalle?",
    ),
    "it": (
        "Vuoi sapere di più su {topic}?",
        "Ti interessa {topic}?",
        "Esploriamo meglio {topic}?",
    ),
    "zh": (
        "您想進一步了解{topic}嗎？",
        "您對{topic}感興趣嗎？",
        "我們一起看看{topic}，好嗎？",
    ),
}
_CHILD_FR = (
    "Veux-tu en savoir plus sur {topic} ?",
    "Aimerais-tu découvrir {topic} ?",
    "On découvre {topic} ensemble ?",
)
_DECLINED = {
    "en": "All right. What else interests you?",
    "fr": "D'accord. Qu'est-ce qui vous intéresse maintenant ?",
    "es": "De acuerdo. ¿Qué más te interesa?",
    "it": "Va bene. Cos'altro ti interessa?",
    "zh": "好的。您現在對什麼感興趣？",
}


def invitation(language: str, next_intent: str, index: int, profile: str) -> str:
    language = language if language in _TOPICS else "en"
    forms = (
        _CHILD_FR
        if language == "fr" and profile in {"child", "early_child"}
        else _FORMS[language]
    )
    return forms[index % len(forms)].format(topic=_TOPICS[language][next_intent])


def declined_reply(language: str) -> str:
    return _DECLINED.get(language, _DECLINED["en"])
