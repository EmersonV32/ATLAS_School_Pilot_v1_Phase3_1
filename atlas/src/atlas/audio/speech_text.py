"""Deterministic speech-only number expansion for French museum answers."""

from __future__ import annotations

import re
from datetime import date

_SMALL = (
    "zéro",
    "un",
    "deux",
    "trois",
    "quatre",
    "cinq",
    "six",
    "sept",
    "huit",
    "neuf",
    "dix",
    "onze",
    "douze",
    "treize",
    "quatorze",
    "quinze",
    "seize",
)
_TENS = ("", "", "vingt", "trente", "quarante", "cinquante", "soixante")
_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)
_CALENDAR_DATE_PATTERN = (
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|"
    r"\d{1,2}\.\d{1,2}\.\d{4})\b"
)
_CALENDAR_DATE = re.compile(_CALENDAR_DATE_PATTERN)
# Leave technical tokens, decimals, and grouped large numbers to the voice.
_PROTECTED = re.compile(
    _CALENDAR_DATE_PATTERN + r"|(?:https?://|www\.)\S+|`[^`]*`|"
    r"\b[\w.+-]+@[\w.-]+\.\w+\b|"
    r"\b\w*[A-Za-z_]\w*(?:[-:/]\w+)+\b|"
    r"\b\d+(?:[.,]\d+)+\b|"
    r"\b\d{1,3}(?:[ \u00a0\u202f]\d{3})+\b"
)
_FIRST_OF_MONTH = re.compile(
    r"\b1(?:er)?(?=\s+(?:" + "|".join(_MONTHS) + r")\b)", re.IGNORECASE
)
_NUMBER = re.compile(r"(?<![\w/#:.+\-])\d{1,4}(?!\w|[.,]\d|[/+])")
_YEAR_RANGE = re.compile(
    r"(?<![\w/#:.+\-])([1-9]\d{3})\s*[-–—]\s*([1-9]\d{3})"
    r"(?!\w|[.,]\d|[/+])"
)
_SPACED_YEAR = re.compile(
    r"\b(en|vers|an|année|années)\s+([1-9](?:[ \u00a0\u202f]+\d){3})"
    r"(?![ \u00a0\u202f]*\d|\w)",
    re.IGNORECASE,
)


def french_number_words(number: int) -> str:
    """Spell an integer from zero through 9999 using standard French forms."""
    if not 0 <= number <= 9999:
        raise ValueError("French speech expansion supports integers 0 through 9999")
    if number < 17:
        return _SMALL[number]
    if number < 20:
        return "dix-" + _SMALL[number - 10]
    if number < 70:
        tens, units = divmod(number, 10)
        return _TENS[tens] + (
            " et un" if units == 1 else "-" + _SMALL[units] if units else ""
        )
    if number < 80:
        return "soixante" + (
            " et onze" if number == 71 else "-" + french_number_words(number - 60)
        )
    if number < 100:
        return (
            "quatre-vingts"
            if number == 80
            else ("quatre-vingt-" + french_number_words(number - 80))
        )
    if number < 1000:
        hundreds, rest = divmod(number, 100)
        prefix = "cent" if hundreds == 1 else _SMALL[hundreds] + " cent"
        return prefix + (
            " " + french_number_words(rest) if rest else ("s" if hundreds > 1 else "")
        )
    thousands, rest = divmod(number, 1000)
    prefix = "mille" if thousands == 1 else _SMALL[thousands] + " mille"
    return prefix + (" " + french_number_words(rest) if rest else "")


def _expand_french_fragment(text: str) -> str:
    text = _FIRST_OF_MONTH.sub("premier", text)
    text = _SPACED_YEAR.sub(
        lambda match: (
            match[1] + " " + french_number_words(int(re.sub(r"\s", "", match[2])))
        ),
        text,
    )
    text = _YEAR_RANGE.sub(
        lambda match: (
            french_number_words(int(match[1]))
            + " à "
            + french_number_words(int(match[2]))
        ),
        text,
    )
    return _NUMBER.sub(lambda match: french_number_words(int(match[0])), text)


def _calendar_date_words(text: str) -> str:
    if re.fullmatch(r"[1-9][ \u00a0\u202f]\d{3}", text):
        return french_number_words(int(re.sub(r"\s", "", text)))
    if not _CALENDAR_DATE.fullmatch(text):
        return text
    values = tuple(map(int, re.split(r"[-/.]", text)))
    year, month, day = values if "-" in text else values[::-1]
    try:
        date(year, month, day)
    except ValueError:
        return text
    return " ".join(
        (
            "premier" if day == 1 else french_number_words(day),
            _MONTHS[month - 1],
            french_number_words(year),
        )
    )


def normalize_speech_text(text: str, language: str) -> str:
    """Expand French dates/numbers immediately before synthesis, never display.

    Other languages and technical tokens remain byte-for-byte unchanged. This
    function is idempotent, so a failed cloud attempt can safely use local TTS.
    """
    if str(language).strip().casefold().split("-", 1)[0] != "fr":
        return text
    parts: list[str] = []
    offset = 0
    for protected in _PROTECTED.finditer(text):
        parts.append(_expand_french_fragment(text[offset : protected.start()]))
        parts.append(_calendar_date_words(protected[0]))
        offset = protected.end()
    parts.append(_expand_french_fragment(text[offset:]))
    return "".join(parts)
