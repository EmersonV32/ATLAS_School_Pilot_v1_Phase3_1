"""SQLite database helper for ATLAS.

Owns the on-disk schema used by keyword retrieval:
  - `chunks`      : one row per ingested chunk, with metadata for filtering
  - `chunks_fts`  : an FTS5 full-text index over chunk text (if FTS5 exists)

FTS5 ships with the standard CPython sqlite3 build on Windows/macOS/Linux.
If a build lacks it, `fts5_available()` returns False and the keyword store
falls back to a pure-Python BM25 over the `chunks` table.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id            TEXT PRIMARY KEY,
    artwork_id          TEXT NOT NULL,
    language            TEXT NOT NULL,
    educational_level   TEXT NOT NULL,
    chunk_type          TEXT NOT NULL,
    text                TEXT NOT NULL,
    source_id           TEXT NOT NULL,
    verified            INTEGER NOT NULL DEFAULT 0,
    allowed_for_students INTEGER NOT NULL DEFAULT 1,
    keywords            TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_chunks_artwork ON chunks(artwork_id);
CREATE INDEX IF NOT EXISTS idx_chunks_lang ON chunks(language);
"""

_FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
USING fts5(chunk_id UNINDEXED, text, keywords);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open (creating parent dirs) a SQLite connection with Row factory."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # The device loop and the integrated dashboard share one retriever.
    # SqliteFtsStore serializes access with a lock.
    con = sqlite3.connect(str(db_path), check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def fts5_available(con: sqlite3.Connection) -> bool:
    """True if this SQLite build supports FTS5."""
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS _fts5_probe USING fts5(x)")
        con.execute("DROP TABLE IF EXISTS _fts5_probe")
        return True
    except sqlite3.OperationalError:
        return False


def init_schema(con: sqlite3.Connection) -> bool:
    """Create the base schema and (if possible) the FTS index.

    Returns True if FTS5 is available, False if the Python BM25 fallback
    will be used.
    """
    con.executescript(_SCHEMA)
    has_fts = fts5_available(con)
    if has_fts:
        con.executescript(_FTS_SCHEMA)
    con.commit()
    return has_fts


def reset(con: sqlite3.Connection) -> None:
    """Drop all ATLAS tables (used by `ingest --reset`)."""
    con.executescript(
        "DROP TABLE IF EXISTS chunks_fts; DROP TABLE IF EXISTS chunks;"
    )
    con.commit()
