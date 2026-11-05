"""Conservative, visit-local small talk; no lookup, model or visitor identity."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def normalized(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text).split())


def ends_conversation(question: str) -> bool:
    return normalized(question) in {
        "au revoir", "merci au revoir", "bonne journee", "a bientot",
        "stop", "arrete", "arretez", "stop talking", "goodbye", "bye",
        "thanks goodbye", "have a good day",
    }


_GREETINGS = {
    "bonjour",
    "bonsoir",
    "salut",
    "coucou",
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
}
_WELLBEING = {
    "comment ca va",
    "comment vas tu",
    "comment allez vous",
    "ca va",
    "comment va tu",
    "comment tu vas",
    "comment vous allez",
    "ca va bien",
    "comment se passe votre journee",
    "comment se passe ta journee",
    "passez vous une bonne journee",
    "passes tu une bonne journee",
    "how are you",
    "how are you doing",
    "how is your day",
    "how s your day",
    "are you having a good day",
    "how do you do",
}
_JOKES = {
    "raconte une blague",
    "raconte moi une blague",
    "dis moi une blague",
    "fais moi rire",
    "une blague",
    "raconte une plaisanterie",
    "raconte moi une plaisanterie",
    "tell me a joke",
    "tell a joke",
    "make me laugh",
    "a joke",
    "another joke",
    "une autre blague",
    "encore une blague",
}
_THANKS = {"merci", "merci beaucoup", "thanks", "thank you", "thanks a lot"}
_GOOD = {
    "bien",
    "tres bien",
    "super",
    "oui",
    "oui merci",
    "bien merci",
    "ca va",
    "ca va bien",
    "je vais bien",
    "je vais bien merci",
    "bien et toi",
    "bien et vous",
    "good",
    "great",
    "fine",
    "yes",
    "i m fine",
    "i am fine",
    "i m good",
    "good thanks",
    "good and you",
    "fine and you",
}
_LOW = {
    "non",
    "pas tres bien",
    "pas bien",
    "je vais mal",
    "bof",
    "no",
    "not good",
    "not great",
    "bad",
    "i m sad",
    "i am sad",
}
_YES = {
    "oui",
    "oui merci",
    "oui s il te plait",
    "oui s il vous plait",
    "avec plaisir",
    "yes",
    "yes please",
    "sure",
    "please",
    "encore",
    "another",
    "une autre",
}
_NO = {"non", "non merci", "no", "no thanks", "no thank you"}


def social_kind(question: str) -> str | None:
    """Match only complete social requests; never swallow a compound question."""
    text = normalized(question)
    if text in _GREETINGS or text in {f"{p} atlas" for p in _GREETINGS}:
        return "greeting"
    for prefix in sorted(_GREETINGS, key=len, reverse=True):
        if text.startswith(prefix + " "):
            text = text[len(prefix) + 1 :]
            break
    if text in _WELLBEING:
        return "wellbeing"
    if text in _JOKES:
        return "joke"
    if text in _THANKS:
        return "thanks"
    return None


@dataclass(frozen=True)
class SocialReply:
    response: str
    kind: str
    follow_up: str


def resolve_social(
    question: str,
    language: str,
    *,
    pending: str | None,
    turn: int,
    profile: str = "",
) -> SocialReply | None:
    """Respond socially first; offer an art-interest bridge only after chatting.

    Pending values are coarse dialogue intents, not sentiment/profile records.
    Other languages keep the ordinary model path in their selected language.
    """
    if language not in {"en", "fr"}:
        return None
    text = normalized(question)
    kind = social_kind(question)
    if pending == "social:wellbeing" and text in _GOOD | _LOW:
        kind = "day_low" if text in _LOW else "day_good"
    elif pending == "social:joke" and text in _YES | _NO:
        kind = "decline" if text in _NO else "joke"
    elif pending == "social:interests" and text in _YES | _NO:
        kind = "decline" if text in _NO else "interests"
    if kind is None:
        return None
    fr = language == "fr"
    next_intent = "social:wellbeing"
    if kind == "greeting":
        answer = (
            "Bonjour ! Comment allez-vous aujourd'hui ?"
            if fr
            else "Hello! How are you today?"
        )
    elif kind == "wellbeing":
        answer = (
            "Merci de demander ! Je suis prêt à discuter avec vous. "
            "Et vous, comment se passe votre journée ?"
            if fr
            else "Thanks for asking! I'm ready to chat with you. How is your day going?"
        )
    elif kind == "day_good":
        if turn >= 2:
            answer = (
                "Ça fait plaisir à entendre ! Qu'est-ce qui vous attire le plus "
                "dans une visite au musée : les histoires, les couleurs "
                "ou les techniques ?"
                if fr
                else "That's good to hear! What interests you most in a museum "
                "visit: stories, colours, or how things were made?"
            )
            next_intent = "social:interests"
        else:
            answer = (
                "Ça fait plaisir à entendre ! Qu'avez-vous envie de faire aujourd'hui ?"
                if fr
                else "That's good to hear! What would you like to do today?"
            )
            next_intent = "social:chat"
    elif kind == "day_low":
        answer = (
            "Merci de me le dire. De quoi avez-vous envie de parler tranquillement ?"
            if fr
            else "Thanks for telling me. What would you like to chat about?"
        )
        next_intent = "social:chat"
    elif kind == "joke":
        jokes = (
            (
                "Un escargot croise une limace et lui dit : "
                "« Tiens, tu as oublié ta maison ! »",
                "Un crayon arrive en retard à l'école. "
                "Il explique qu'il avait mauvaise mine.",
            )
            if fr
            else (
                "A snail sees a slug and says, 'You forgot your house!'",
                "I tried to catch some fog yesterday. I mist.",
            )
        )
        answer = jokes[turn % len(jokes)] + (
            " Voulez-vous une autre blague ?" if fr else " Would you like another joke?"
        )
        next_intent = "social:joke"
    elif kind == "thanks":
        answer = (
            "Avec plaisir ! De quoi aimeriez-vous parler maintenant ?"
            if fr
            else "You're welcome! What would you like to talk about now?"
        )
        next_intent = "social:chat"
    elif kind == "interests":
        answer = (
            "Vous préférez les histoires, les couleurs ou les techniques ?"
            if fr
            else "Do you prefer stories, colours, or how things were made?"
        )
        next_intent = "social:interests"
    else:
        answer = (
            "D'accord, on peut simplement discuter. De quoi avez-vous envie de parler ?"
            if fr
            else "All right, we can just chat. What would you like to talk about?"
        )
        next_intent = "social:chat"
    if fr and profile in {"early_child", "child"}:
        for formal, informal in (
            ("Comment allez-vous", "Comment vas-tu"),
            ("avec vous", "avec toi"),
            ("Et vous", "Et toi"),
            ("votre journée", "ta journée"),
            ("vous attire", "t'attire"),
            ("Qu'avez-vous", "Qu'as-tu"),
            ("avez-vous", "as-tu"),
            ("Voulez-vous", "Veux-tu"),
            ("aimeriez-vous", "aimerais-tu"),
            ("Vous préférez", "Tu préfères"),
        ):
            answer = answer.replace(formal, informal)
    return SocialReply(answer, kind, next_intent)
