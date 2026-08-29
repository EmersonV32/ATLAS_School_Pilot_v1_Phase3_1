"""Content pack models: a pack is a manifest plus a set of artworks."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from atlas.models.artwork import Artwork
from atlas.models.enums import EducationalLevel, Language


class ContentPackManifest(BaseModel):
    """Metadata describing a content pack (the manifest.json file)."""

    model_config = ConfigDict(extra="forbid")

    pack_id: str
    name: str
    version: str
    description: str = ""
    languages: list[Language] = Field(default_factory=list)
    educational_levels: list[EducationalLevel] = Field(default_factory=list)
    artwork_files: list[str] = Field(default_factory=list)


class ContentPack(BaseModel):
    """A fully loaded content pack: manifest + parsed artworks.

    Built in memory by the ingestion pipeline (Phase 2). Held here so the
    schema can be validated independently of the ingest code.
    """

    model_config = ConfigDict(extra="forbid")

    manifest: ContentPackManifest
    artworks: list[Artwork] = Field(default_factory=list)

    @property
    def artwork_ids(self) -> list[str]:
        return [a.artwork_id for a in self.artworks]
