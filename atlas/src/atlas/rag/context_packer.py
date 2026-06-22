"""Context packing.

Turns a RetrievalResult into a compact, attributable context block for the
LLM prompt. Includes only the top chunks, each tagged with its chunk_id and
source_id so the grounding validator (Phase 3) can check that the answer
cites real, retrieved chunks. Bounded by a character budget.
"""

from __future__ import annotations

from atlas.models.retrieval import RetrievalResult


class PackedContext:
    """Result of packing: the prompt text plus the chunk_ids included."""

    def __init__(self, context_text: str, chunk_ids: list[str]) -> None:
        self.context_text = context_text
        self.chunk_ids = chunk_ids

    def is_empty(self) -> bool:
        return not self.chunk_ids


def pack_context(
    result: RetrievalResult,
    *,
    max_chars: int = 1200,
    min_score: float | None = None,
) -> PackedContext:
    """Pack top chunks into a bounded, tagged context string.

    Chunks below `min_score` (if given) are dropped before packing, which
    lets the dialogue layer refuse to answer when nothing relevant was
    retrieved.
    """
    lines: list[str] = []
    included: list[str] = []
    used = 0

    for chunk in result.chunks:
        if min_score is not None and chunk.score < min_score:
            continue
        block = (
            f"[chunk_id={chunk.chunk_id} source_id={chunk.source_id}] "
            f"{chunk.text}"
        )
        if used + len(block) > max_chars and included:
            break
        lines.append(block)
        included.append(chunk.chunk_id)
        used += len(block)

    return PackedContext("\n".join(lines), included)
