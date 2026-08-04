"""Phase 2 tests for Reciprocal Rank Fusion."""

from __future__ import annotations

from atlas.models.retrieval import RetrievedChunk
from atlas.rag.fusion import reciprocal_rank_fusion


def _chunk(cid: str, rank: int, retriever: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=cid,
        artwork_id="a1",
        text=f"text {cid}",
        source_id="s1",
        rank=rank,
        retriever=retriever,
    )


def test_rrf_rewards_agreement() -> None:
    # c1 is ranked #1 by both lists; c2 only by one; c3 only by the other.
    dense = [_chunk("c1", 1, "dense"), _chunk("c2", 2, "dense")]
    keyword = [_chunk("c1", 1, "keyword"), _chunk("c3", 2, "keyword")]
    fused = reciprocal_rank_fusion([dense, keyword], k=60)
    assert fused[0].chunk_id == "c1"
    assert {c.chunk_id for c in fused} == {"c1", "c2", "c3"}
    assert fused[0].retriever == "fused"


def test_rrf_formula_value() -> None:
    # Single list, single item at rank 1 -> 1/(k+1).
    only = [_chunk("c1", 1, "dense")]
    fused = reciprocal_rank_fusion([only], k=60)
    assert abs(fused[0].score - (1.0 / 61)) < 1e-9


def test_rrf_ranks_are_sequential() -> None:
    dense = [_chunk("c1", 1, "dense"), _chunk("c2", 2, "dense"),
             _chunk("c3", 3, "dense")]
    fused = reciprocal_rank_fusion([dense], k=60)
    assert [c.rank for c in fused] == [1, 2, 3]


def test_rrf_empty_input() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[]]) == []
