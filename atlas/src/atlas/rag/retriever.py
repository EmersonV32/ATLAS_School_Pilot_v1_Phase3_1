"""Hybrid retriever: dense + keyword, fused with RRF, then reranked.

Pipeline (spec Steps B-F):
  1. light query normalization (preserve meaning; raw kept upstream)
  2. dense retrieval (vector store) with metadata filters
  3. keyword retrieval (SQLite FTS5/BM25) with the same filters
  4. Reciprocal Rank Fusion
  5. reranking (heuristic by default)
Returns a RetrievalResult with per-stage latencies.
"""

from __future__ import annotations

import threading

from atlas.config.settings import RagSettings
from atlas.models.retrieval import RetrievalQuery, RetrievalResult, RetrievedChunk
from atlas.rag.chroma_store import VectorStoreBase
from atlas.rag.embeddings import EmbedderBase
from atlas.rag.fusion import reciprocal_rank_fusion
from atlas.rag.reranker import HeuristicReranker, RerankerBase
from atlas.rag.sqlite_fts_store import SqliteFtsStore
from atlas.utils.text import clean_asr, looks_like_pronoun_only
from atlas.utils.time import Timer


class HybridRetriever:
    def __init__(
        self,
        embedder: EmbedderBase,
        vector_store: VectorStoreBase,
        fts_store: SqliteFtsStore,
        settings: RagSettings,
        reranker: RerankerBase | None = None,
        artwork_titles: dict[str, str] | None = None,
    ) -> None:
        self.embedder = embedder
        self.vector_store = vector_store
        self.fts_store = fts_store
        self.settings = settings
        self.reranker = reranker or HeuristicReranker()
        self._retrieve_lock = threading.Lock()
        # Optional map of artwork_id -> title for pronoun disambiguation.
        self.artwork_titles = artwork_titles or {}

    def normalize_query(self, query: RetrievalQuery) -> str:
        """Light normalization. Never changes meaning.

        If the query is vague (pronoun-led) and we know the detected
        artwork's title, append the title so retrieval has an anchor.
        """
        text = clean_asr(query.text)
        if (
            query.artwork_id
            and looks_like_pronoun_only(text)
            and query.artwork_id in self.artwork_titles
        ):
            text = f"{text} ({self.artwork_titles[query.artwork_id]})"
        return text

    # Content packs are not required to provide every educational level.
    # When the requested level has no chunks, fall back to this general
    # level so profiles like visual_impairment still get grounded answers.
    FALLBACK_LEVEL = "adult_beginner"

    def _search_at_level(
        self,
        normalized: str,
        query: RetrievalQuery,
        level: str,
        language: str,
    ) -> tuple[list[list[RetrievedChunk]], float | None, float | None]:
        rankings: list[list[RetrievedChunk]] = []
        dense_ms = keyword_ms = None

        if self.settings.use_dense:
            with Timer() as t:
                vector = self.embedder.embed_one(normalized)
                dense_hits = self.vector_store.query(
                    vector,
                    artwork_id=query.artwork_id,
                    language=language,
                    educational_level=level,
                    top_k=self.settings.dense_top_k,
                )
            dense_ms = t.elapsed_ms
            rankings.append(dense_hits)

        if self.settings.use_keyword:
            with Timer() as t:
                keyword_hits = self.fts_store.search(
                    normalized,
                    artwork_id=query.artwork_id,
                    language=language,
                    educational_level=level,
                    top_k=self.settings.keyword_top_k,
                )
            keyword_ms = t.elapsed_ms
            rankings.append(keyword_hits)

        return rankings, dense_ms, keyword_ms

    def _search_with_level_fallback(
        self, normalized: str, query: RetrievalQuery, language: str
    ) -> tuple[list[list[RetrievedChunk]], float, float]:
        """Search one language, retrying the general level when necessary."""
        level = query.educational_level.value
        rankings, dense_ms, keyword_ms = self._search_at_level(
            normalized, query, level, language
        )
        total_dense = dense_ms or 0.0
        total_keyword = keyword_ms or 0.0

        if not any(rankings) and level != self.FALLBACK_LEVEL:
            rankings, dense_ms, keyword_ms = self._search_at_level(
                normalized, query, self.FALLBACK_LEVEL, language
            )
            total_dense += dense_ms or 0.0
            total_keyword += keyword_ms or 0.0
        return rankings, total_dense, total_keyword

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """Serialize shared model and SQLite access across runtime/UI threads."""
        with self._retrieve_lock:
            return self._retrieve_unlocked(query)

    def _retrieve_unlocked(self, query: RetrievalQuery) -> RetrievalResult:
        normalized = self.normalize_query(query)

        requested_language = query.language.value
        rankings, dense_ms, keyword_ms = self._search_with_level_fallback(
            normalized, query, requested_language
        )

        target_k = query.top_k or self.settings.top_k
        native_count = len(
            reciprocal_rank_fusion(rankings, k=self.settings.rrf_k)
        )
        fallback_language = self.settings.fallback_language
        if (
            self.settings.language_fallback_enabled
            and requested_language != fallback_language
            and native_count < target_k
        ):
            fallback_rankings, fallback_dense_ms, fallback_keyword_ms = (
                self._search_with_level_fallback(
                    normalized, query, fallback_language
                )
            )
            rankings.extend(fallback_rankings)
            dense_ms += fallback_dense_ms
            keyword_ms += fallback_keyword_ms

        with Timer() as total:
            fused = reciprocal_rank_fusion(rankings, k=self.settings.rrf_k)
            reranked = self.reranker.rerank(query, fused)
            top = reranked[:target_k]

        return RetrievalResult(
            query=query,
            chunks=top,
            dense_latency_ms=dense_ms,
            keyword_latency_ms=keyword_ms,
            total_latency_ms=(dense_ms or 0)
            + (keyword_ms or 0)
            + total.elapsed_ms,
        )
