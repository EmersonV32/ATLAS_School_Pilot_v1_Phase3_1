"""Phase 1 tests for the content schema (artwork / chunk / source)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from atlas.models.artwork import Artwork, Chunk, Source
from atlas.models.enums import ChunkType, EducationalLevel, Language


def _valid_artwork_dict() -> dict:
    return {
        "artwork_id": "starry_night",
        "title": "The Starry Night",
        "artist": "Vincent van Gogh",
        "date": "1889",
        "materials": "Oil on canvas",
        "dimensions": "73.7 cm x 92.1 cm",
        "culture_origin": "Dutch / Post-Impressionist",
        "movement": "Post-Impressionism",
        "official_description": "A night sky over a village.",
        "historical_context": "Painted during the artist's stay in 1889.",
        "visual_description": "Swirling sky, bright stars, a tall cypress.",
        "themes": ["night", "nature", "emotion"],
        "keywords": ["sky", "stars", "village", "cypress"],
        "supported_languages": ["en", "fr"],
        "educational_levels": ["child", "adult_beginner"],
        "sources": [
            {
                "source_id": "src_demo_1",
                "title": "Demo educational note",
                "url": "https://example.org/starry-night",
                "publisher": "ATLAS demo pack",
                "license_note": "Placeholder educational text, not museum copy.",
                "last_checked": "2026-06-01",
            }
        ],
        "chunks": [
            {
                "chunk_id": "starry_night_visual_en_1",
                "artwork_id": "starry_night",
                "language": "en",
                "educational_level": "adult_beginner",
                "chunk_type": "visual_description",
                "text": "The sky swirls with motion above a quiet village.",
                "source_id": "src_demo_1",
                "verified": True,
                "allowed_for_students": True,
                "keywords": ["sky", "village"],
            }
        ],
    }


def test_valid_artwork_parses() -> None:
    art = Artwork.model_validate(_valid_artwork_dict())
    assert art.artwork_id == "starry_night"
    assert art.chunks[0].language is Language.EN
    assert art.chunks[0].chunk_type is ChunkType.VISUAL_DESCRIPTION
    assert art.validate_source_links() == []


def test_chunk_artwork_id_must_match() -> None:
    data = _valid_artwork_dict()
    data["chunks"][0]["artwork_id"] = "wrong_id"
    with pytest.raises(ValidationError):
        Artwork.model_validate(data)


def test_empty_chunk_text_rejected() -> None:
    with pytest.raises(ValidationError):
        Chunk(
            chunk_id="c1",
            artwork_id="a1",
            language=Language.EN,
            educational_level=EducationalLevel.CHILD,
            chunk_type=ChunkType.FACT,
            text="   ",
            source_id="s1",
        )


def test_unknown_source_link_detected() -> None:
    data = _valid_artwork_dict()
    data["chunks"][0]["source_id"] = "src_missing"
    art = Artwork.model_validate(data)
    assert art.validate_source_links() == ["starry_night_visual_en_1"]


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        Source(
            source_id="s1",
            title="t",
            url="https://example.org",
            publisher="p",
            license_note="n",
            last_checked="2026-06-01",
            sneaky="nope",
        )
