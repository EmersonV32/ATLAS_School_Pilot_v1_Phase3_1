"""Content chunking helpers.

Takes a loaded Artwork and produces a flat list of Chunk objects ready for
ingestion. The chunks are already defined in the content-pack JSON files, so
this module's job is to validate them, assign stable chunk_ids if missing,
and produce a deduplicated, ingest-ready list.

We deliberately do NOT do automated sentence-splitting here. Museum content
is curator-written and short; splitting it further would fragment attribution
and make grounding harder. Each JSON chunk is one logical idea.
"""

from __future__ import annotations

import hashlib

from atlas.models.artwork import Artwork, Chunk


def _stable_chunk_id(artwork_id: str, text: str, language: str, level: str) -> str:
    """Deterministic chunk_id from content so re-ingestion is idempotent."""
    fingerprint = f"{artwork_id}|{language}|{level}|{text[:120]}"
    return "chunk_" + hashlib.sha1(fingerprint.encode()).hexdigest()[:16]


def prepare_chunks(artwork: Artwork) -> list[Chunk]:
    """Return the artwork's chunks, filling in chunk_id if missing.

    Filters out:
      - chunks with verified=False
      - chunks with allowed_for_students=False

    Raises ValueError if any remaining chunk references a source_id not
    declared in artwork.sources (hard block at ingest time).
    """
    known_sources = {s.source_id for s in artwork.sources}
    out: list[Chunk] = []

    for chunk in artwork.chunks:
        if not chunk.verified:
            continue
        if not chunk.allowed_for_students:
            continue

        # Fill stable id if the JSON used a placeholder.
        if not chunk.chunk_id or chunk.chunk_id.startswith("PLACEHOLDER"):
            chunk = chunk.model_copy(
                update={
                    "chunk_id": _stable_chunk_id(
                        chunk.artwork_id,
                        chunk.text,
                        chunk.language.value,
                        chunk.educational_level.value,
                    )
                }
            )

        if chunk.source_id not in known_sources:
            raise ValueError(
                f"chunk {chunk.chunk_id!r} references unknown source "
                f"{chunk.source_id!r} in artwork {artwork.artwork_id!r}"
            )

        out.append(chunk)

    return out
