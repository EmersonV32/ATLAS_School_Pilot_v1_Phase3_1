"""Retrieval models shared by the hybrid RAG pipeline (Phase 2)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from atlas.models.enums import EducationalLevel, Intent, Language


class RetrievalQuery(BaseModel):
    """Normalized input to the retriever."""

    model_config = ConfigDict(extra="forbid")

    text: str
    artwork_id: str | None = None
    language: Language = Language.EN
    educational_level: EducationalLevel = EducationalLevel.ADULT_BEGINNER
    intent: Intent = Intent.UNKNOWN
    top_k: int = 5


class RetrievedChunk(BaseModel):
    """A chunk returned by a retriever, with its score and provenance.

    The optional metadata fields (chunk_type, language, educational_level,
    keywords) are populated by the stores so the reranker can apply
    intent/language/level boosts without a second lookup.
    """

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    artwork_id: str
    text: str
    source_id: str
    score: float = 0.0
    rank: int = 0
    retriever: str = ""  # "dense" | "keyword" | "fused" | "reranked"
    chunk_type: str | None = None
    language: str | None = None
    educational_level: str | None = None
    keywords: list[str] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    """Final ranked set handed to the context packer."""

    model_config = ConfigDict(extra="forbid")

    query: RetrievalQuery
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    dense_latency_ms: float | None = None
    keyword_latency_ms: float | None = None
    total_latency_ms: float | None = None
