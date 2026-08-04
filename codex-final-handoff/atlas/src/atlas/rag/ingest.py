"""Content-pack ingestion.

Loads and validates a content pack (manifest + artwork JSON), prepares
chunks, and writes them to both the vector store (dense) and the SQLite FTS
store (keyword). Idempotent: re-running upserts by chunk_id.

CLI:
    python -m atlas.rag.ingest --pack data/content_packs/demo_pack
    python -m atlas.rag.ingest --pack data/content_packs/demo_pack --reset
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from atlas.config.loader import load_settings
from atlas.config.settings import Settings
from atlas.models.artwork import Artwork
from atlas.models.content_pack import ContentPack, ContentPackManifest
from atlas.models.enums import RunMode
from atlas.rag.chunking import prepare_chunks
from atlas.rag.chroma_store import (
    ChromaVectorStore,
    SimpleVectorStore,
    VectorStoreBase,
)
from atlas.rag.embeddings import make_embedder
from atlas.models.retrieval import RetrievedChunk
from atlas.rag.sqlite_fts_store import SqliteFtsStore
from atlas.storage import sqlite_db


def load_content_pack(pack_dir: str | Path) -> ContentPack:
    """Read and validate a content pack from disk."""
    pack_dir = Path(pack_dir)
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"no manifest.json in {pack_dir}")
    manifest = ContentPackManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    artworks: list[Artwork] = []
    for rel in manifest.artwork_files:
        path = pack_dir / rel
        artworks.append(
            Artwork.model_validate_json(path.read_text(encoding="utf-8"))
        )
    return ContentPack(manifest=manifest, artworks=artworks)


def build_vector_store(settings: Settings) -> VectorStoreBase:
    """Pick the dense store for the current mode."""
    if settings.mode == RunMode.DEV:
        return SimpleVectorStore(
            persist_path=Path(settings.paths.chroma_dir) / "dev_vectors.json"
        )
    return ChromaVectorStore(persist_dir=settings.paths.chroma_dir)


def ingest_pack(settings: Settings, pack_dir: str | Path, *, reset: bool = False) -> dict:
    pack = load_content_pack(pack_dir)

    embedder = make_embedder(
        settings.rag, mock=(settings.mode == RunMode.DEV)
    )
    vector_store = build_vector_store(settings)

    db_path = Path(settings.paths.sqlite_dir) / "atlas.db"
    if reset:
        vector_store.reset()
        con = sqlite_db.connect(db_path)
        sqlite_db.reset(con)
        con.close()
    fts_store = SqliteFtsStore(db_path)

    total_chunks = 0
    for artwork in pack.artworks:
        chunks = prepare_chunks(
            artwork, max_words=settings.rag.chunk_max_words
        )
        if not chunks:
            continue

        # Vector store records.
        vectors = embedder.embed([c.text for c in chunks])
        records = []
        for chunk, vector in zip(chunks, vectors):
            records.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "vector": vector,
                    "text": chunk.text,
                    "metadata": {
                        "artwork_id": chunk.artwork_id,
                        "language": chunk.language.value,
                        "educational_level": chunk.educational_level.value,
                        "chunk_type": chunk.chunk_type.value,
                        "source_id": chunk.source_id,
                        "verified": chunk.verified,
                        "allowed_for_students": chunk.allowed_for_students,
                        "keywords": chunk.keywords,
                    },
                }
            )
        vector_store.add(records)

        # Keyword store records.
        kw_chunks = [
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
        fts_store.add_chunks(kw_chunks)
        total_chunks += len(chunks)

    return {
        "pack_id": pack.manifest.pack_id,
        "artworks": len(pack.artworks),
        "chunks_ingested": total_chunks,
        "vector_count": vector_store.count(),
        "fts_count": fts_store.count(),
        "fts5": fts_store.has_fts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest an ATLAS content pack")
    parser.add_argument("--pack", required=True, help="Path to the pack dir")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--mode", default=None, choices=[m.value for m in RunMode])
    parser.add_argument("--reset", action="store_true", help="Drop tables first")
    args = parser.parse_args()

    settings = load_settings(args.config_dir)
    if args.mode:
        settings.mode = RunMode(args.mode)

    summary = ingest_pack(settings, args.pack, reset=args.reset)
    print("Ingestion complete:")
    for key, value in summary.items():
        print(f"  {key:18}: {value}")


if __name__ == "__main__":
    main()
