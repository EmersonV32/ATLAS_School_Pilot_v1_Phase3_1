"""Reranking.

Phase 2 ships a transparent heuristic reranker. It nudges the fused order
using signals the LLM cares about: the detected artwork, the requested
language, and whether the chunk type matches the question's intent. A
cross-encoder reranker can be dropped in later behind the same interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from atlas.models.enums import Intent
from atlas.models.retrieval import RetrievalQuery, RetrievedChunk

# Which chunk types best answer each intent.
_INTENT_CHUNK_TYPES: dict[Intent, set[str]] = {
    Intent.WHAT_IS_THIS: {"official_description", "general"},
    Intent.WHO_MADE_IT: {"fact", "official_description"},
    Intent.WHEN_MADE: {"fact", "historical_context"},
    Intent.HOW_MADE: {"technique", "fact"},
    Intent.MEANING: {"theme", "historical_context"},
    Intent.VISUAL: {"visual_description"},
    Intent.HISTORY: {"historical_context", "fact"},
}

ARTWORK_MATCH_BOOST = 0.50
ARTWORK_MISMATCH_PENALTY = 0.50
LANGUAGE_MATCH_BOOST = 0.05
INTENT_MATCH_BOOST = 0.15


class RerankerBase(ABC):
    @abstractmethod
    def rerank(
        self, query: RetrievalQuery, chunks: list[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        ...


class HeuristicReranker(RerankerBase):
    """Score adjustments layered on top of the fused score."""

    def rerank(self, query, chunks):
        preferred = _INTENT_CHUNK_TYPES.get(query.intent, set())
        rescored: list[RetrievedChunk] = []
        for c in chunks:
            score = c.score
            if query.artwork_id:
                if c.artwork_id == query.artwork_id:
                    score += ARTWORK_MATCH_BOOST
                else:
                    score -= ARTWORK_MISMATCH_PENALTY
            if c.language and c.language == query.language.value:
                score += LANGUAGE_MATCH_BOOST
            if preferred and c.chunk_type in preferred:
                score += INTENT_MATCH_BOOST
            rescored.append(c.model_copy(update={"score": score}))

        rescored.sort(key=lambda x: x.score, reverse=True)
        return [
            c.model_copy(update={"rank": i, "retriever": "reranked"})
            for i, c in enumerate(rescored, start=1)
        ]


class CrossEncoderReranker(RerankerBase):
    """Extension point. Wraps a sentence-transformers CrossEncoder.

    Not enabled by default (settings.rag.use_cross_encoder_reranker). Lazy
    imports so the dependency is only needed when actually switched on.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise ImportError(
                    'Cross-encoder reranking needs the rag extra: '
                    'pip install -e ".[rag]"'
                ) from exc
            self._model = CrossEncoder(self._model_name)

    def rerank(self, query, chunks):
        if not chunks:
            return chunks
        self._load()
        pairs = [(query.text, c.text) for c in chunks]
        scores = self._model.predict(pairs)
        rescored = [
            c.model_copy(update={"score": float(s)})
            for c, s in zip(chunks, scores)
        ]
        rescored.sort(key=lambda x: x.score, reverse=True)
        return [
            c.model_copy(update={"rank": i, "retriever": "reranked"})
            for i, c in enumerate(rescored, start=1)
        ]
