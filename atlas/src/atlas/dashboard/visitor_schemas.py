"""Privacy-bounded schemas for the visitor onboarding API.

Progress intentionally has no visitor name or exact age. Start accepts one
short greeting name for the local-only speech path; it is never projected back.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from atlas.dashboard.visitor_activation import clean_greeting_name

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
AgeGuidance = Literal["under_7", "under_13", "13_17", "18_plus"]
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


class VisitorStartRequest(BaseModel):
    """A visit-only name used only by the Jetson's private local path."""

    model_config = ConfigDict(extra="forbid")

    greeting_name: str | None = Field(default=None, max_length=40)

    @field_validator("greeting_name")
    @classmethod
    def validate_greeting_name(cls, value: str | None) -> str | None:
        return clean_greeting_name(value)


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
