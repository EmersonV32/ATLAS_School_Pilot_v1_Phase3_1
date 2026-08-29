"""Keyword retrieval over SQLite.

Primary path: FTS5 with the built-in `bm25()` ranking function. Fallback:
a compact pure-Python BM25 over the `chunks` table (used only if the local
SQLite build lacks FTS5). Both honour the same metadata filters:
artwork_id, language, educational_level, allowed_for_students, verified.
"""

from __future__ import annotations

import math
import re
import sqlite3
import threading
from collections import Counter
from pathlib import Path

from atlas.models.retrieval import RetrievedChunk
from atlas.storage import sqlite_db

_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _fts_match_expr(query: str) -> str:
    """Build a safe FTS5 MATCH expression: OR of quoted tokens."""
    tokens = _tokenize(query)
    if not tokens:
        return '""'
    return " OR ".join(f'"{t}"' for t in tokens)


class SqliteFtsStore:
    """Keyword store backed by SQLite (FTS5 when available)."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._lock = threading.RLock()
        self.con = sqlite_db.connect(self.db_path)
        self.has_fts = sqlite_db.init_schema(self.con)

    # -- ingestion -------------------------------------------------------
    def add_chunks(self, chunks: list[RetrievedChunk]) -> int:
        """Insert chunk rows (and FTS rows). Idempotent on chunk_id."""
        with self._lock:
            cur = self.con.cursor()
            for c in chunks:
                cur.execute(
                    """INSERT OR REPLACE INTO chunks
                       (chunk_id, artwork_id, language, educational_level,
                        chunk_type, text, source_id, verified,
                        allowed_for_students, keywords)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        c.chunk_id,
                        c.artwork_id,
                        c.language or "",
                        c.educational_level or "",
                        c.chunk_type or "",
                        c.text,
                        c.source_id,
                        1,
                        1,
                        " ".join(c.keywords),
                    ),
                )
                if self.has_fts:
                    cur.execute(
                        "DELETE FROM chunks_fts WHERE chunk_id = ?", (c.chunk_id,)
                    )
                    cur.execute(
                        "INSERT INTO chunks_fts (chunk_id, text, keywords) "
                        "VALUES (?,?,?)",
                        (c.chunk_id, c.text, " ".join(c.keywords)),
                    )
            self.con.commit()
        return len(chunks)

    def count(self) -> int:
        with self._lock:
            return self.con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    # -- retrieval -------------------------------------------------------
    def search(
        self,
        query: str,
        *,
        artwork_id: str | None,
        language: str,
        educational_level: str,
        top_k: int,
    ) -> list[RetrievedChunk]:
        with self._lock:
            if self.has_fts:
                rows = self._search_fts(
                    query, artwork_id, language, educational_level, top_k
                )
            else:
                rows = self._search_python_bm25(
                    query, artwork_id, language, educational_level, top_k
                )
        results: list[RetrievedChunk] = []
        for rank, (row, score) in enumerate(rows, start=1):
            results.append(
                RetrievedChunk(
                    chunk_id=row["chunk_id"],
                    artwork_id=row["artwork_id"],
                    text=row["text"],
                    source_id=row["source_id"],
                    score=score,
                    rank=rank,
                    retriever="keyword",
                    chunk_type=row["chunk_type"],
                    language=row["language"],
                    educational_level=row["educational_level"],
                    keywords=row["keywords"].split() if row["keywords"] else [],
                )
            )
        return results

    def _filters(
        self, artwork_id: str | None, language: str, level: str
    ) -> tuple[str, list]:
        clauses = [
            "c.verified = 1",
            "c.allowed_for_students = 1",
            "c.language = ?",
            "c.educational_level = ?",
        ]
        params: list = [language, level]
        if artwork_id:
            clauses.append("c.artwork_id = ?")
            params.append(artwork_id)
        return " AND ".join(clauses), params

    def _search_fts(self, query, artwork_id, language, level, top_k):
        where, params = self._filters(artwork_id, language, level)
        sql = f"""
            SELECT c.*, bm25(chunks_fts) AS bm
            FROM chunks_fts
            JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
            WHERE chunks_fts MATCH ? AND {where}
            ORDER BY bm ASC
            LIMIT ?
        """
        match = _fts_match_expr(query)
        try:
            rows = self.con.execute(sql, [match, *params, top_k]).fetchall()
        except sqlite3.OperationalError:
            return []
        # bm25 returns lower = better (often negative). Flip to positive score.
        return [(r, -float(r["bm"])) for r in rows]

    def _search_python_bm25(self, query, artwork_id, language, level, top_k):
        where, params = self._filters(artwork_id, language, level)
        rows = self.con.execute(
            f"SELECT c.* FROM chunks c WHERE {where}", params
        ).fetchall()
        if not rows:
            return []
        docs = [_tokenize(r["text"] + " " + (r["keywords"] or "")) for r in rows]
        scored = _bm25(_tokenize(query), docs)
        ranked = sorted(
            zip(rows, scored, strict=True), key=lambda t: t[1], reverse=True
        )[:top_k]
        return [(r, s) for r, s in ranked if s > 0] or ranked[:top_k]


def _bm25(query_tokens: list[str], docs: list[list[str]], k1: float = 1.5,
          b: float = 0.75) -> list[float]:
    """Compact BM25 Okapi scoring fallback."""
    n = len(docs)
    if n == 0:
        return []
    avgdl = sum(len(d) for d in docs) / n
    df: Counter[str] = Counter()
    for d in docs:
        for term in set(d):
            df[term] += 1
    scores = [0.0] * n
    q = set(query_tokens)
    for i, d in enumerate(docs):
        tf = Counter(d)
        dl = len(d) or 1
        for term in q:
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            freq = tf[term]
            denom = freq + k1 * (1 - b + b * dl / avgdl)
            scores[i] += idf * (freq * (k1 + 1)) / denom
    return scores
