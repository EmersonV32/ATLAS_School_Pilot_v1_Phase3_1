"""Phase 2 integration test for the hybrid retriever.

Ingests the demo pack into temporary stores (dev embedder + SQLite FTS) and
checks that queries return the right artwork's chunks, that language and
artwork filters are honoured, and that an off-topic query for an artwork
still stays within that artwork.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from atlas.config.settings import RagSettings
from atlas.models.enums import EducationalLevel, Intent, Language
from atlas.models.retrieval import RetrievalQuery, RetrievedChunk
from atlas.rag.chroma_store import SimpleVectorStore
from atlas.rag.chunking import prepare_chunks
from atlas.rag.embeddings import (
    MockEmbedder,
    SentenceTransformerEmbedder,
    make_embedder,
)
from atlas.rag.ingest import load_content_pack
from atlas.rag.retriever import HybridRetriever
from atlas.rag.sqlite_fts_store import SqliteFtsStore

PACK_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "content_packs"
    / "demo_pack"
)


def test_real_embedder_defaults_to_cached_files_only():
    embedder = make_embedder(RagSettings())
    assert isinstance(embedder, SentenceTransformerEmbedder)
    assert embedder._local_files_only is True


def test_sqlite_store_supports_integrated_dashboard_thread(tmp_path):
    store = SqliteFtsStore(tmp_path / "shared.db")
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(store.count).result() == 0


def test_simple_vector_reset_clears_persisted_records(tmp_path) -> None:
    path = tmp_path / "vecs.json"
    store = SimpleVectorStore(persist_path=path)
    store.add(
        [
            {
                "chunk_id": "old",
                "vector": [1.0, 0.0],
                "text": "stale content",
                "metadata": {},
            }
        ]
    )

    store.reset()

    assert store.count() == 0
    assert SimpleVectorStore(persist_path=path).count() == 0


@pytest.fixture()
def retriever(tmp_path) -> HybridRetriever:
    settings = RagSettings()
    embedder = MockEmbedder()
    vector_store = SimpleVectorStore(persist_path=tmp_path / "vecs.json")
    fts_store = SqliteFtsStore(tmp_path / "atlas.db")

    pack = load_content_pack(PACK_DIR)
    titles = {a.artwork_id: a.title for a in pack.artworks}
    for artwork in pack.artworks:
        chunks = prepare_chunks(artwork)
        vectors = embedder.embed([c.text for c in chunks])
        vector_store.add(
            [
                {
                    "chunk_id": c.chunk_id,
                    "vector": v,
                    "text": c.text,
                    "metadata": {
                        "artwork_id": c.artwork_id,
                        "language": c.language.value,
                        "educational_level": c.educational_level.value,
                        "chunk_type": c.chunk_type.value,
                        "source_id": c.source_id,
                        "verified": c.verified,
                        "allowed_for_students": c.allowed_for_students,
                        "keywords": c.keywords,
                    },
                }
                for c, v in zip(chunks, vectors, strict=True)
            ]
        )
        fts_store.add_chunks(
            [
                RetrievedChunk(
                    chunk_id=c.chunk_id,
                    artwork_id=c.artwork_id,
                    text=c.text,
                    source_id=c.source_id,
                    chunk_type=c.chunk_type.value,
                    language=c.language.value,
                    educational_level=c.educational_level.value,
                    keywords=c.keywords,
                )
                for c in chunks
            ]
        )

    return HybridRetriever(
        embedder=embedder,
        vector_store=vector_store,
        fts_store=fts_store,
        settings=settings,
        artwork_titles=titles,
    )


def test_retrieves_correct_artwork(retriever: HybridRetriever) -> None:
    result = retriever.retrieve(
        RetrievalQuery(
            text="why is the sky swirling with stars",
            artwork_id="starry_night",
            language=Language.EN,
            educational_level=EducationalLevel.ADULT_BEGINNER,
            intent=Intent.VISUAL,
            top_k=3,
        )
    )
    assert result.chunks, "expected at least one chunk"
    assert all(c.artwork_id == "starry_night" for c in result.chunks)


def test_language_filter_isolates_french(retriever: HybridRetriever) -> None:
    result = retriever.retrieve(
        RetrievalQuery(
            text="qui a peint la nuit etoilee",
            artwork_id="starry_night",
            language=Language.FR,
            educational_level=EducationalLevel.ADULT_BEGINNER,
            intent=Intent.WHO_MADE_IT,
            top_k=3,
        )
    )
    assert result.chunks
    assert all(c.language == "fr" for c in result.chunks)


def test_missing_language_falls_back_to_english(retriever: HybridRetriever) -> None:
    result = retriever.retrieve(
        RetrievalQuery(
            text="quien pinto la noche estrellada",
            artwork_id="starry_night",
            language=Language.ES,
            educational_level=EducationalLevel.ADULT_BEGINNER,
            intent=Intent.WHO_MADE_IT,
            top_k=3,
        )
    )
    assert result.chunks
    assert all(c.language == "en" for c in result.chunks)


def test_artwork_filter_excludes_others(retriever: HybridRetriever) -> None:
    # Ask a gold/pharaoh question but scoped to mona_lisa: must not leak
    # Tutankhamun chunks in.
    result = retriever.retrieve(
        RetrievalQuery(
            text="tell me about the gold mask",
            artwork_id="mona_lisa",
            language=Language.EN,
            educational_level=EducationalLevel.ADULT_BEGINNER,
            intent=Intent.GENERAL,
            top_k=5,
        )
    )
    assert all(c.artwork_id == "mona_lisa" for c in result.chunks)


def test_visual_intent_prefers_visual_chunk(retriever: HybridRetriever) -> None:
    result = retriever.retrieve(
        RetrievalQuery(
            text="what does it look like",
            artwork_id="tutankhamun_mask",
            language=Language.EN,
            educational_level=EducationalLevel.ADULT_BEGINNER,
            intent=Intent.VISUAL,
            top_k=3,
        )
    )
    assert result.chunks
    # The visual-description chunk should rank at or near the top.
    top_types = [c.chunk_type for c in result.chunks[:2]]
    assert "visual_description" in top_types
