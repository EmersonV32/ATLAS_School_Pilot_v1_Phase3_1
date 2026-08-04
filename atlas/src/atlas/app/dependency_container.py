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
        self._vision_detector = None
        self._artwork_tracker = None
        self._stt = None
        self._tts = None
        self._hardware = None
        self._session_runner = None

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

            use_gemini = (
                self.settings.llm.provider == "gemini"
                and self.settings.llm.cloud_llm_enabled
                and self.settings.mode in (RunMode.DEVICE, RunMode.DEMO)
            )
            if use_gemini:
                from atlas.dialogue.gemini_client import GeminiClient

                llm = GeminiClient(
                    model=self.settings.llm.model,
                    api_key=None,  # reads the env var at call time
                )
            else:
                from atlas.dialogue.mock_llm_client import MockLLMClient

                llm = MockLLMClient()
            self._dialogue_engine = DialogueEngine(
                llm_client=llm, expect_json=use_gemini
            )
        return self._dialogue_engine

    # --- Phase 4: perception, speech, hardware, pipeline ---------------
    @property
    def vision_detector(self):
        if self._vision_detector is None:
            if self.settings.mode == RunMode.DEVICE:
                from atlas.vision.yolo_detector import YoloDetector
                self._vision_detector = YoloDetector(
                    model_path=self.settings.hardware.yolo_model_path,
                    conf_threshold=0.65,
                )
            else:
                from atlas.vision.mock_detector import MockDetector
                self._vision_detector = MockDetector()
        return self._vision_detector

    @property
    def artwork_tracker(self):
        if self._artwork_tracker is None:
            from atlas.vision.tracker import ArtworkTracker

            titles = self._artwork_titles()
            self._artwork_tracker = ArtworkTracker(
                detector=self.vision_detector,
                conf_threshold=0.65,
                stability_frames=3,
                valid_artwork_ids=set(titles) or None,
            )
        return self._artwork_tracker

    @property
    def stt(self):
        if self._stt is None:
            if self.settings.mode == RunMode.DEVICE:
                from atlas.audio.whisper_stt import WhisperSTT
                self._stt = WhisperSTT(
                    model_size=self.settings.hardware.whisper_model_size,
                    compute_type=self.settings.hardware.whisper_compute_type,
                )
            else:
                from atlas.audio.mock_stt import MockSTT
                self._stt = MockSTT()
        return self._stt

    @property
    def tts(self):
        if self._tts is None:
            if self.settings.mode == RunMode.DEVICE:
                from atlas.audio.piper_tts import PiperTTS
                self._tts = PiperTTS(
                    voice_en=self.settings.hardware.piper_voice_en,
                    voice_fr=self.settings.hardware.piper_voice_fr,
                    piper_binary=self.settings.hardware.piper_binary_path or "piper",
                )
            else:
                from atlas.audio.mock_tts import MockTTS
                self._tts = MockTTS()
        return self._tts

    @property
    def hardware(self):
        if self._hardware is None:
            use_ev3 = (
                self.settings.mode == RunMode.DEVICE
                and self.settings.hardware.enable_ev3
                and self.settings.hardware.ev3_bt_address
            )
            if use_ev3:
                from atlas.hardware.ev3_hardware import EV3Hardware
                self._hardware = EV3Hardware(
                    bt_address=self.settings.hardware.ev3_bt_address
                )
            else:
                from atlas.hardware.mock_hardware import MockHardware
                self._hardware = MockHardware()
        return self._hardware

    @property
    def session_runner(self):
        if self._session_runner is None:
            from atlas.pipeline.session_runner import SessionRunner, make_retriever
            self._session_runner = SessionRunner(
                detector=self.artwork_tracker,
                stt=self.stt,
                tts=self.tts,
                hardware=self.hardware,
                dialogue_engine=self.dialogue_engine,
                retriever=make_retriever(self.retriever),
            )
        return self._session_runner

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
