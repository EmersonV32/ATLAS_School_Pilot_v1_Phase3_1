"""Dense vector retrieval.

Two implementations behind one interface:
  - SimpleVectorStore: pure-Python cosine similarity with optional JSON
    persistence. Runs in dev with zero extra installs and persists across
    `ingest` and `query` commands.
  - ChromaVectorStore: real ChromaDB (lazy import; `pip install -e ".[rag]"`).

Both apply the same metadata filters as the keyword store.
"""

from __future__ import annotations

import json
import math
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from atlas.models.retrieval import RetrievedChunk


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def _passes(meta: dict[str, Any], artwork_id, language, level) -> bool:
    if not meta.get("verified"):
        return False
    if not meta.get("allowed_for_students"):
        return False
    if meta.get("language") != language:
        return False
    if meta.get("educational_level") != level:
        return False
    if artwork_id and meta.get("artwork_id") != artwork_id:
        return False
    return True


class VectorStoreBase(ABC):
    @abstractmethod
    def add(self, items: list[dict[str, Any]]) -> int:
        """Add records: {chunk_id, vector, text, metadata}."""

    @abstractmethod
    def query(
        self,
        vector: list[float],
        *,
        artwork_id: str | None,
        language: str,
        educational_level: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        ...

    @abstractmethod
    def count(self) -> int:
        ...

    @abstractmethod
    def reset(self) -> None:
        """Remove all records while keeping the store ready for ingestion."""


class SimpleVectorStore(VectorStoreBase):
    """In-process cosine store with optional JSON persistence (dev mode)."""

    def __init__(self, persist_path: str | Path | None = None) -> None:
        self.persist_path = Path(persist_path) if persist_path else None
        self._records: list[dict[str, Any]] = []
        if self.persist_path and self.persist_path.exists():
            self._records = json.loads(
                self.persist_path.read_text(encoding="utf-8")
            )

    def add(self, items: list[dict[str, Any]]) -> int:
        by_id = {r["chunk_id"]: r for r in self._records}
        for it in items:
            by_id[it["chunk_id"]] = it
        self._records = list(by_id.values())
        self._save()
        return len(items)

    def _save(self) -> None:
        if self.persist_path:
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            self.persist_path.write_text(
                json.dumps(self._records, ensure_ascii=False),
                encoding="utf-8",
            )

    def count(self) -> int:
        return len(self._records)

    def reset(self) -> None:
        self._records = []
        self._save()

    def query(self, vector, *, artwork_id, language, educational_level, top_k):
        scored: list[tuple[float, dict[str, Any]]] = []
        for rec in self._records:
            meta = rec["metadata"]
            if not _passes(meta, artwork_id, language, educational_level):
                continue
            scored.append((_cosine(vector, rec["vector"]), rec))
        scored.sort(key=lambda t: t[0], reverse=True)
        out: list[RetrievedChunk] = []
        for rank, (score, rec) in enumerate(scored[:top_k], start=1):
            meta = rec["metadata"]
            out.append(
                RetrievedChunk(
                    chunk_id=rec["chunk_id"],
                    artwork_id=meta["artwork_id"],
                    text=rec["text"],
                    source_id=meta["source_id"],
                    score=float(score),
                    rank=rank,
                    retriever="dense",
                    chunk_type=meta.get("chunk_type"),
                    language=meta.get("language"),
                    educational_level=meta.get("educational_level"),
                    keywords=meta.get("keywords", []),
                )
            )
        return out


class ChromaVectorStore(VectorStoreBase):
    """Real ChromaDB-backed store (lazy import)."""

    def __init__(self, persist_dir: str | Path, collection: str = "atlas") -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise ImportError(
                'ChromaDB is not installed. Run: pip install -e ".[rag]"'
            ) from exc
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection_name = collection
        self._col = self._client.get_or_create_collection(collection)

    def add(self, items: list[dict[str, Any]]) -> int:
        self._col.upsert(
            ids=[it["chunk_id"] for it in items],
            embeddings=[it["vector"] for it in items],
            documents=[it["text"] for it in items],
            metadatas=[_flatten_meta(it["metadata"]) for it in items],
        )
        return len(items)

    def count(self) -> int:
        return self._col.count()

    def reset(self) -> None:
        self._client.delete_collection(self._collection_name)
        self._col = self._client.get_or_create_collection(
            self._collection_name
        )

    def query(self, vector, *, artwork_id, language, educational_level, top_k):
        where: dict[str, Any] = {
            "$and": [
                {"language": language},
                {"educational_level": educational_level},
                {"verified": True},
                {"allowed_for_students": True},
            ]
        }
        if artwork_id:
            where["$and"].append({"artwork_id": artwork_id})
        res = self._col.query(
            query_embeddings=[vector], n_results=top_k, where=where
        )
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        out: list[RetrievedChunk] = []
        for rank, (cid, doc, meta, dist) in enumerate(
            zip(ids, docs, metas, dists), start=1
        ):
            out.append(
                RetrievedChunk(
                    chunk_id=cid,
                    artwork_id=meta["artwork_id"],
                    text=doc,
                    source_id=meta["source_id"],
                    score=1.0 - float(dist),  # distance -> similarity
                    rank=rank,
                    retriever="dense",
                    chunk_type=meta.get("chunk_type"),
                    language=meta.get("language"),
                    educational_level=meta.get("educational_level"),
                    keywords=(meta.get("keywords") or "").split(),
                )
            )
        return out


def _flatten_meta(meta: dict[str, Any]) -> dict[str, Any]:
    """Chroma metadata values must be primitives; join keyword lists."""
    flat = dict(meta)
    if isinstance(flat.get("keywords"), list):
        flat["keywords"] = " ".join(flat["keywords"])
    return flat
