"""Language metadata shared by the admin UI and runtime providers."""

from __future__ import annotations

from dataclasses import dataclass

from atlas.models.enums import Language


@dataclass(frozen=True)
class AdminLanguageOption:
    code: str
    label: str
    prompt_name: str


# Ordered for the operator: broadest likely judge usefulness first. Every entry
# is supported by the configured Cartesia Sonic, Deepgram Nova-3, and Whisper
# provider families. The public visitor onboarding intentionally uses its own,
# smaller validated language list.
ADMIN_LANGUAGE_OPTIONS = (
    AdminLanguageOption(Language.EN.value, "English", "English"),
    AdminLanguageOption(
        Language.ZH.value,
        "Chinese (Mandarin)",
        "Traditional Chinese",
    ),
    AdminLanguageOption(Language.HI.value, "Hindi", "Hindi"),
    AdminLanguageOption(Language.ES.value, "Spanish", "Spanish"),
    AdminLanguageOption(Language.FR.value, "French", "French"),
    AdminLanguageOption(Language.AR.value, "Arabic", "Arabic"),
    AdminLanguageOption(Language.BN.value, "Bengali", "Bengali"),
    AdminLanguageOption(Language.PT.value, "Portuguese", "Portuguese"),
    AdminLanguageOption(Language.RU.value, "Russian", "Russian"),
    AdminLanguageOption(Language.ID.value, "Indonesian", "Indonesian"),
    AdminLanguageOption(Language.DE.value, "German", "German"),
    AdminLanguageOption(Language.JA.value, "Japanese", "Japanese"),
    AdminLanguageOption(Language.TE.value, "Telugu", "Telugu"),
    AdminLanguageOption(Language.TR.value, "Turkish", "Turkish"),
    AdminLanguageOption(Language.KO.value, "Korean", "Korean"),
    AdminLanguageOption(Language.VI.value, "Vietnamese", "Vietnamese"),
    AdminLanguageOption(Language.IT.value, "Italian", "Italian"),
    AdminLanguageOption(Language.TA.value, "Tamil", "Tamil"),
    AdminLanguageOption(Language.TH.value, "Thai", "Thai"),
    AdminLanguageOption(Language.PL.value, "Polish", "Polish"),
)

ADMIN_LANGUAGE_CODES = frozenset(option.code for option in ADMIN_LANGUAGE_OPTIONS)
OUTPUT_LANGUAGE_NAMES = {
    option.code: option.prompt_name for option in ADMIN_LANGUAGE_OPTIONS
}


def normalize_language_code(value: object, fallback: str = "en") -> str:
    """Normalize a BCP-47-like value to an enabled ATLAS language code."""
    normalized = str(value or "").strip().lower().split("-", 1)[0]
    return normalized if normalized in ADMIN_LANGUAGE_CODES else fallback
