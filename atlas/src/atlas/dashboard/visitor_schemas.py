"""Privacy-bounded schemas for the visitor onboarding API.

The API intentionally has no field for a visitor's name or exact age. The
browser reduces those answers to a boolean and broad guidance band before it
updates the mock-backed state machine.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VisitorLanguage = Literal["en", "fr", "es", "it", "ar", "zh-Hant"]
VisitorStep = Literal[
    "welcome",
    "language",
    "about",
    "expertise",
    "interests",
    "accessibility",
    "headset",
    "readiness",
    "privacy",
]
AgeGuidance = Literal["under_13", "13_17", "18_plus"]
ExpertiseLevel = Literal["curious", "familiar", "enthusiast"]
AccessibilityChoice = Literal[
    "audio_description", "simple_language", "slower_pace", "none"
]


class VisitorProgressRequest(BaseModel):
    """Only coarse, non-identifying personalization may cross the API."""

    model_config = ConfigDict(extra="forbid")

    step: VisitorStep
    language: VisitorLanguage | None = None
    name_entered: bool = False
    age_guidance: AgeGuidance | None = None
    expertise: ExpertiseLevel | None = None
    interests: list[str] = Field(default_factory=list, max_length=6)
    accessibility: list[AccessibilityChoice] = Field(
        default_factory=list, max_length=3
    )


class VisitorHelpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context: Literal["onboarding", "headset", "readiness", "experience"]
    message: str | None = Field(default=None, max_length=120)


class VisitorSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: Literal[
        "reset",
        "ready",
        "unit_unavailable",
        "headset_attention",
        "connection_lost",
        "transfer_failure",
    ]
