"""Dependency container.

A single place that constructs and holds shared components, so real Jetson
modules can replace mocks by swapping what the container builds. Phase 1
wired settings + logger; Phase 2 adds the embedder, vector store, keyword
store, and the hybrid retriever. Vision, audio, LLM, and hardware follow the
same dependency-injection pattern in later phases.
"""

from __future__ import annotations

from pathlib import Path

from atlas.config.loader import load_settings
from atlas.config.settings import Settings
from atlas.models.enums import RunMode
from atlas.storage.event_logger import EventLogger


class Container:
    """Lazily-built application components."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._logger: EventLogger | None = None
        self._embedder = None
        self._vector_store = None
        self._fts_store = None
        self._retriever = None
        self._dialogue_engine = None

    @property
    def logger(self) -> EventLogger:
        if self._logger is None:
            self._logger = EventLogger(
                logs_dir=self.settings.paths.logs_dir,
                settings=self.settings.logging,
            )
        return self._logger

    # --- Phase 2: retrieval --------------------------------------------
    @property
    def embedder(self):
        if self._embedder is None:
            from atlas.rag.embeddings import make_embedder

            self._embedder = make_embedder(
                self.settings.rag, mock=(self.settings.mode == RunMode.DEV)
            )
        return self._embedder

    @property
    def vector_store(self):
        if self._vector_store is None:
            from atlas.rag.ingest import build_vector_store

            self._vector_store = build_vector_store(self.settings)
        return self._vector_store

    @property
    def fts_store(self):
        if self._fts_store is None:
            from atlas.rag.sqlite_fts_store import SqliteFtsStore

            db_path = Path(self.settings.paths.sqlite_dir) / "atlas.db"
            self._fts_store = SqliteFtsStore(db_path)
        return self._fts_store

    def _artwork_titles(self) -> dict[str, str]:
        """Load artwork_id -> title from the default pack, if present."""
        from atlas.rag.ingest import load_content_pack

        pack_dir = (
            Path(self.settings.paths.content_packs_dir)
            / self.settings.default_pack_id
        )
        if not (pack_dir / "manifest.json").exists():
            return {}
        try:
            pack = load_content_pack(pack_dir)
        except Exception:
            return {}
        return {a.artwork_id: a.title for a in pack.artworks}

    @property
    def retriever(self):
        if self._retriever is None:
            from atlas.rag.retriever import HybridRetriever

            self._retriever = HybridRetriever(
                embedder=self.embedder,
                vector_store=self.vector_store,
                fts_store=self.fts_store,
                settings=self.settings.rag,
                artwork_titles=self._artwork_titles(),
            )
        return self._retriever

    # --- Phase 3: dialogue ---------------------------------------------
    @property
    def dialogue_engine(self):
        if self._dialogue_engine is None:
            from atlas.dialogue.dialogue_engine import DialogueEngine

            if self.settings.mode in (RunMode.DEVICE, RunMode.DEMO):
                from atlas.dialogue.gemini_client import GeminiClient

                llm = GeminiClient(
                    model=self.settings.llm.model,
                    api_key=None,  # reads GEMINI_API_KEY env var at call time
                )
            else:
                from atlas.dialogue.mock_llm_client import MockLLMClient

                llm = MockLLMClient()
            self._dialogue_engine = DialogueEngine(llm_client=llm)
        return self._dialogue_engine

    # --- Extension points (filled in later phases) ----------------------
    # self.vision_detector   -> VisionDetector (mock/yolo)   [Phase 4]
    # self.stt               -> STTBase (mock/whisper)       [Phase 4]
    # self.tts               -> TTSBase (mock/piper)         [Phase 4]
    # self.llm_client        -> LLMBase (mock/gemini)        [Phase 3]
    # self.hardware          -> HardwareController (mock/ev3)[Phase 4]


def build_container(config_dir: str | Path = "config") -> Container:
    """Construct a Container from on-disk configuration."""
    settings = load_settings(config_dir)
    return Container(settings)
