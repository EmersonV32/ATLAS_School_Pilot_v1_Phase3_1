"""Local routing hints for vocabulary follow-ups, not stored visitor data."""

from __future__ import annotations

import re
import unicodedata

_EXPLICIT_WORD = re.compile(
    r"\b(?:word|words|term|terms|vocabulary|define|definition|"
    r"mot|mots|terme|termes|vocabulaire|definis|definir|definition|"
    r"palabra|palabras|termino|terminos|definicion|"
    r"parola|parole|termine|termini|definizione)\b|"
    r"(?:這個詞|这个词|詞語|词语|術語|术语|這個字|这个字)"
)
_SHORT_MEANING = (
    re.compile(r"\bwhat does (?P<term>[\w-]+) mean\b"),
    re.compile(
        r"\b(?:que signifie|que veut dire) "
        r"(?:(?:le|la|l|un|une) )?(?P<term>[\w-]+)\b"
    ),
    re.compile(
        r"\b(?:que significa|cosa significa|che significa) "
        r"(?:(?:el|la|il|un|una) )?(?P<term>[\w-]+)\b"
    ),
    re.compile(r"\bwhat do you mean by (?P<term>[\w-]+)\b"),
    re.compile(
        r"\b(?:ca veut dire quoi|c est quoi) "
        r"(?:(?:le|la|l|un|une) )?(?P<term>[\w-]+)\b"
    ),
    re.compile(r"\bwhat is (?:(?:a|an|the) )?(?P<term>[\w-]+)\s*$"),
    re.compile(r"\b(?:what is|what s) the meaning of (?P<term>[\w-]+)\s*$"),
    re.compile(r"(?P<term>[\w-]{1,24})(?:是什麼意思|是什么意思|的意思是什麼|的意思是什么)"),
)
_REFERENCES = {
    "it", "this", "that", "ceci", "cela", "ca", "cette", "cet", "ce", "le", "la",
    "esto", "eso", "esta", "este", "el", "lo", "questo", "questa", "quello", "il",
    "這幅畫", "这幅画", "這件作品", "这件作品", "它", "這個", "这个",
}
_CLARIFICATION = re.compile(
    r"\b(?:mean|means|meaning|define|definition|signif\w*|defin\w*|"
    r"dire|quoi|why|pourquoi|explica\w*|spiega\w*)\b|"
    r"\bexplain (?:the |this |that )?(?:word|term)\b|"
    r"\bexplique\w* (?:moi |nous )?(?:le |ce |un )?(?:mot|terme)\b|"
    r"(?:意思|解釋|解释|什麼|什么)"
)


def asks_word_meaning(question: str) -> bool:
    """Keep word definitions out of canned whole-artwork interpretations.

    The model also receives a general multilingual vocabulary rule. These
    conservative hints only protect the five languages with local FAQ answers;
    no word list limits what Gemini can explain.
    """
    text = unicodedata.normalize("NFKD", str(question).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = " ".join(re.sub(r"[^\w]+", " ", text).split())
    if _EXPLICIT_WORD.search(text) and _CLARIFICATION.search(text):
        return True
    for pattern in _SHORT_MEANING:
        match = pattern.search(text)
        if match and match.group("term") not in _REFERENCES:
            return True
    return False
