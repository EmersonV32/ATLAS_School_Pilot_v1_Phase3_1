"""Session and visitor-profile models.

Sessions are anonymous: identified only by a generated session_id. No
student names, no facial recognition, no inferred attributes.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from atlas.models.enums import EducationalLevel, Language


class SessionProfile(BaseModel):
    """Adaptation settings for a session.

    Controls language, explanation level, and accessibility behavior.
    """

    model_config = ConfigDict(extra="forbid")

    language: Language = Language.EN
    educational_level: EducationalLevel = EducationalLevel.ADULT_BEGINNER
    expert_mode: bool = False
    verbose_allowed: bool = False  # only true for expert / visual_impairment

    def normalized(self) -> "SessionProfile":
        """Return a profile with verbose_allowed derived from the level."""
        verbose = self.educational_level in (
            EducationalLevel.EXPERT,
            EducationalLevel.VISUAL_IMPAIRMENT,
        )
        return self.model_copy(update={"verbose_allowed": verbose})


class Session(BaseModel):
    """An anonymous interaction session."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    pack_id: str | None = None
    profile: SessionProfile = Field(default_factory=SessionProfile)
    manual_artwork_id: str | None = None
    active: bool = True
    started_at: str = ""  # ISO timestamp
    stopped_at: str | None = None
