"""Shared enumerations used across ATLAS models.

Kept in one module to avoid circular imports between model files.
ATLAS uses an edge-first architecture: vision, speech, retrieval, motor
control, and text-to-speech run locally or nearby, while the current
prototype uses a cloud language model for final response generation.
A future version aims to replace this with an on-device language model.
"""

from __future__ import annotations

from enum import Enum


class Language(str, Enum):
    """Supported visitor languages.

    English and French are required for the school-pilot MVP.
    Spanish and Italian are optional/demo-level.
    """

    EN = "en"
    FR = "fr"
    ES = "es"
    IT = "it"


class EducationalLevel(str, Enum):
    """Explanation level / accessibility profile applied to an answer."""

    CHILD = "child"
    TEEN = "teen"
    ADULT_BEGINNER = "adult_beginner"
    EXPERT = "expert"
    VISUAL_IMPAIRMENT = "visual_impairment"
    SIMPLE_LANGUAGE = "simple_language"


class ChunkType(str, Enum):
    """Semantic role of a content chunk, used for intent-aware retrieval."""

    OFFICIAL_DESCRIPTION = "official_description"
    HISTORICAL_CONTEXT = "historical_context"
    VISUAL_DESCRIPTION = "visual_description"
    THEME = "theme"
    FACT = "fact"
    TECHNIQUE = "technique"
    GENERAL = "general"


class Intent(str, Enum):
    """Classified intent of a visitor question."""

    WHAT_IS_THIS = "what_is_this"
    WHO_MADE_IT = "who_made_it"
    WHEN_MADE = "when_made"
    HOW_MADE = "how_made"
    MEANING = "meaning"
    VISUAL = "visual"
    HISTORY = "history"
    GENERAL = "general"
    UNKNOWN = "unknown"


class RunMode(str, Enum):
    """Application run modes.

    DEV: everything mocked, no hardware, no ML downloads.
    LOCAL: real RAG, mock vision/audio.
    DEVICE: real vision/STT/TTS on Jetson.
    DEMO: fixed artwork + typed questions.
    """

    DEV = "dev"
    LOCAL = "local"
    DEVICE = "device"
    DEMO = "demo"
