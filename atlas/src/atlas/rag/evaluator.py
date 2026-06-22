"""Small retrieval evaluation harness.

Given labeled cases (query + expected artwork/chunk), reports hit-rate@k and
mean reciprocal rank. Useful for catching regressions when the retrieval
weights or reranker change. Not a benchmark, just a guardrail.
"""

from __future__ import annotations

from dataclasses import dataclass

from atlas.models.enums import EducationalLevel, Intent, Language
from atlas.models.retrieval import RetrievalQuery
from atlas.rag.retriever import HybridRetriever


@dataclass
class EvalCase:
    query: str
    artwork_id: str | None
    language: Language
    educational_level: EducationalLevel
    intent: Intent
    expected_chunk_ids: list[str]


@dataclass
class EvalReport:
    n: int
    hit_rate_at_k: float
    mrr: float


def evaluate(
    retriever: HybridRetriever, cases: list[EvalCase], k: int = 5
) -> EvalReport:
    hits = 0
    reciprocal = 0.0
    for case in cases:
        result = retriever.retrieve(
            RetrievalQuery(
                text=case.query,
                artwork_id=case.artwork_id,
                language=case.language,
                educational_level=case.educational_level,
                intent=case.intent,
                top_k=k,
            )
        )
        ids = [c.chunk_id for c in result.chunks[:k]]
        rank = next(
            (i for i, cid in enumerate(ids, start=1)
             if cid in case.expected_chunk_ids),
            None,
        )
        if rank is not None:
            hits += 1
            reciprocal += 1.0 / rank
    n = len(cases) or 1
    return EvalReport(
        n=len(cases),
        hit_rate_at_k=hits / n,
        mrr=reciprocal / n,
    )
