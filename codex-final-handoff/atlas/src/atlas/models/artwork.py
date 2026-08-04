"""Pydantic models for artwork content, chunks, and sources.

These define the validated shape of the artwork JSON files in a content
pack. All retrieval-facing text lives in `chunks`; every chunk points at a
`source` so answers can be grounded and attributed.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from atlas.models.enums import ChunkType, EducationalLevel, Language


class Source(BaseModel):
    """A citable source backing one or more chunks.

    We never copy long copyrighted museum text; sources carry attribution
    and a license note so teachers can verify provenance.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: str
    title: str
    url: str
    publisher: str
    license_note: str
    last_checked: str  # ISO date string, e.g. "2026-06-01"


class Chunk(BaseModel):
    """A single retrievable unit of grounded content."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    artwork_id: str
    language: Language
    educational_level: EducationalLevel
    chunk_type: ChunkType
    text: str = Field(min_length=1)
    source_id: str
    verified: bool = False
    allowed_for_students: bool = True
    keywords: list[str] = Field(default_factory=list)

    @field_validator("text")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("chunk text must not be empty after stripping")
        return v


class Artwork(BaseModel):
    """A single artwork, including descriptive metadata, chunks, and sources."""

    model_config = ConfigDict(extra="forbid")

    artwork_id: str
    title: str
    artist: str
    date: str
    materials: str
    dimensions: str
    culture_origin: str
    movement: str
    official_description: str
    historical_context: str
    visual_description: str
    themes: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    supported_languages: list[Language] = Field(default_factory=list)
    educational_levels: list[EducationalLevel] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)

    @field_validator("chunks")
    @classmethod
    def _chunks_reference_artwork(cls, chunks: list[Chunk], info) -> list[Chunk]:
        artwork_id = info.data.get("artwork_id")
        if artwork_id is None:
            return chunks
        for chunk in chunks:
            if chunk.artwork_id != artwork_id:
                raise ValueError(
                    f"chunk {chunk.chunk_id} has artwork_id "
                    f"{chunk.artwork_id!r}, expected {artwork_id!r}"
                )
        return chunks

    def validate_source_links(self) -> list[str]:
        """Return a list of chunk_ids whose source_id is not declared.

        Not raised automatically so ingestion can decide how strict to be,
        but the content schema test asserts this returns empty for the pack.
        """
        known = {s.source_id for s in self.sources}
        return [c.chunk_id for c in self.chunks if c.source_id not in known]
