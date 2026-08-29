"""Dialogue models: requests into the answer service and structured
responses out of the LLM layer.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from atlas.models.enums import EducationalLevel, Intent, Language
from atlas.models.session import SessionProfile


class AskRequest(BaseModel):
    """A question entering the answer service.

    `raw_transcript` is preserved for logs (when transcript logging is
    enabled); `query` may be a lightly rewritten version used for retrieval.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: str
    raw_transcript: str
    query: str | None = None
    artwork_id: str | None = None
    language: Language = Language.EN
    educational_level: EducationalLevel = EducationalLevel.ADULT_BEGINNER
    intent: Intent = Intent.UNKNOWN


class LLMRequest(BaseModel):
    """The fully assembled request handed to an LLM client."""

    model_config = ConfigDict(extra="forbid")

    system_prompt: str
    user_prompt: str
    language: Language
    profile: SessionProfile
    context_chunk_ids: list[str] = Field(default_factory=list)
    allow_regenerate: bool = True


class LLMResponse(BaseModel):
    """Structured response returned by every LLM client (real or mock)."""

    model_config = ConfigDict(extra="forbid")

    spoken_answer: str
    used_chunk_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    unsupported_claims: list[str] = Field(default_factory=list)
    fallback_used: bool = False


class AnswerResult(BaseModel):
    """Final, validated answer ready to be spoken."""

    model_config = ConfigDict(extra="forbid")

    spoken_answer: str
    language: Language
    used_chunk_ids: list[str] = Field(default_factory=list)
    grounded: bool = True
    fallback_used: bool = False
    validation_errors: list[str] = Field(default_factory=list)
