"""Validate and, when needed, split curator-written content chunks."""

from __future__ import annotations

import hashlib
import re

from atlas.models.artwork import Artwork, Chunk


def _stable_chunk_id(artwork_id: str, text: str, language: str, level: str) -> str:
    """Deterministic chunk_id from content so re-ingestion is idempotent."""
    fingerprint = f"{artwork_id}|{language}|{level}|{text[:120]}"
    return "chunk_" + hashlib.sha1(fingerprint.encode()).hexdigest()[:16]


def _split_text(text: str, max_words: int) -> list[str]:
    """Split oversized text at sentence boundaries, then by words as a fallback."""
    if len(text.split()) <= max_words:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    parts: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            parts.append(" ".join(current))
            current.clear()

    for sentence in sentences:
        words = sentence.split()
        if len(words) > max_words:
            flush()
            parts.extend(
                " ".join(words[start : start + max_words])
                for start in range(0, len(words), max_words)
            )
            continue
        if current and len(current) + len(words) > max_words:
            flush()
        current.extend(words)
    flush()
    return parts


def prepare_chunks(artwork: Artwork, *, max_words: int = 55) -> list[Chunk]:
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

        pieces = _split_text(chunk.text, max_words)
        if len(pieces) == 1:
            out.append(chunk)
            continue

        out.extend(
            chunk.model_copy(
                update={
                    "chunk_id": f"{chunk.chunk_id}__{index:02d}",
                    "text": piece,
                }
            )
            for index, piece in enumerate(pieces, start=1)
        )

    # Duplicate IDs would silently overwrite vector/FTS records.
    ids = [chunk.chunk_id for chunk in out]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate chunk_id in artwork {artwork.artwork_id!r}")
    return out
