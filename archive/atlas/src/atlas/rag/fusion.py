"""Reciprocal Rank Fusion (RRF).

Combines several ranked lists into one. For each list, a chunk at 1-based
rank r contributes 1 / (k + r) to its fused score; contributions sum across
lists. Default k = 60 (Cormack et al.). RRF needs only ranks, so it is
robust to dense and keyword scores living on different scales.
"""

from __future__ import annotations

from atlas.models.retrieval import RetrievedChunk

DEFAULT_K = 60


def reciprocal_rank_fusion(
    rankings: list[list[RetrievedChunk]],
    *,
    k: int = DEFAULT_K,
) -> list[RetrievedChunk]:
    """Fuse multiple ranked lists into a single ranked list.

    The representative RetrievedChunk for each id is taken from the first
    list in which it appears (metadata is identical across stores). The
    returned chunks carry the fused score, a fresh 1-based rank, and
    retriever="fused".
    """
    fused_score: dict[str, float] = {}
    representative: dict[str, RetrievedChunk] = {}

    for ranking in rankings:
        for chunk in ranking:
            rank = chunk.rank if chunk.rank > 0 else (ranking.index(chunk) + 1)
            fused_score[chunk.chunk_id] = fused_score.get(chunk.chunk_id, 0.0) + (
                1.0 / (k + rank)
            )
            representative.setdefault(chunk.chunk_id, chunk)

    ordered = sorted(
        fused_score.items(), key=lambda kv: kv[1], reverse=True
    )
    out: list[RetrievedChunk] = []
    for new_rank, (chunk_id, score) in enumerate(ordered, start=1):
        base = representative[chunk_id]
        out.append(
            base.model_copy(
                update={"score": score, "rank": new_rank, "retriever": "fused"}
            )
        )
    return out
