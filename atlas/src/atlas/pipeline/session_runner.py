"""
SessionRunner: one full interaction cycle.

Flow:
  detect -> listen -> retrieve -> dialogue -> speak -> hardware

The retriever argument is a plain callable:
  retriever(artwork_id: str, query: str) -> list[dict[str, str]]

This bridges Phase 2's ContextPack to Phase 3's DialogueEngine without
coupling SessionRunner to either module's internals. See make_retriever()
below for the ready-made adapter when you have a real Phase 2 Retriever.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from atlas.vision.detector import ArtworkDetection, BaseDetector
from atlas.audio.stt import TranscriptResult, BaseSTT
from atlas.audio.tts import BaseTTS
from atlas.hardware.base import BaseHardware, StandCommand
from atlas.dialogue.dialogue_engine import DialogueEngine, DialogueResult

logger = logging.getLogger(__name__)


def _age_hint_to_number(age_hint):
    mapping = {"child": 8, "teen": 14, "adult": 30}
    if isinstance(age_hint, int):
        return age_hint
    return mapping.get(str(age_hint).lower())

RetrieverFn = Callable[[str, str], list[dict]]


@dataclass
class SessionResult:
    detection: Optional[ArtworkDetection]
    transcript: Optional[TranscriptResult]
    dialogue: Optional[DialogueResult]
    error: Optional[str] = None
    tts_ok: bool = True  # False = tts_fallback_used (answer shown as text)

    @property
    def success(self) -> bool:
        return self.error is None and self.dialogue is not None


def make_retriever(phase2_retriever) -> RetrieverFn:
    """
    Wrap a Phase 2 HybridRetriever into the (artwork_id, query) -> list[dict]
    callable that SessionRunner expects.

    The real retriever takes a RetrievalQuery (Pydantic) and returns a
    RetrievalResult with .chunks (each a RetrievedChunk with .text/.chunk_id).
    Only `text` is required on the query; language is mapped from the
    transcript, everything else uses sensible defaults.

    Usage in dependency_container.py:
        from atlas.pipeline.session_runner import make_retriever
        retriever_fn = make_retriever(container.retriever)
    """
    from atlas.rag.retriever import RetrievalQuery
    from atlas.models.enums import Language

    def _lang(code: str) -> Language:
        try:
            return Language(str(code).lower())
        except ValueError:
            return Language.EN

    def _retrieve(artwork_id: str, query: str, language: str = "en") -> list[dict]:
        try:
            rq = RetrievalQuery(
                text=query,
                artwork_id=artwork_id,
                language=_lang(language),
            )
            result = phase2_retriever.retrieve(rq)
            return [
                {"text": chunk.text, "chunk_id": getattr(chunk, "chunk_id", "")}
                for chunk in result.chunks
            ]
        except Exception as exc:
            logger.warning("Retriever error: %s", exc)
            return []
    return _retrieve


class SessionRunner:
    """
    Stateless orchestrator for one detect->respond cycle.
    Construct once; call run_once() in a loop.
    """

    def __init__(
        self,
        detector: BaseDetector,
        stt: BaseSTT,
        tts: BaseTTS,
        hardware: BaseHardware,
        dialogue_engine: DialogueEngine,
        retriever: RetrieverFn,
        listen_duration_s: float = 5.0,
    ) -> None:
        self._detector = detector
        self._stt = stt
        self._tts = tts
        self._hw = hardware
        self._engine = dialogue_engine
        self._retriever = retriever
        self._listen_s = listen_duration_s

    def run_once(self, frame: Any = None) -> SessionResult:
        """Run one full cycle. frame can be a camera frame or None (mock)."""

        # Step 1: detect artwork
        detection = self._detector.detect(frame)
        if detection is None:
            logger.debug("No artwork detected — skipping cycle.")
            return SessionResult(detection=None, transcript=None, dialogue=None,
                                 error="no_detection")

        logger.info("Detected: %s (%.0f%%)", detection.label, detection.confidence * 100)
        self._hw.set_status_led("amber")

        # Step 2: listen for visitor question
        transcript = self._stt.listen(duration_s=self._listen_s)
        if transcript is None or not transcript.text.strip():
            self._hw.set_status_led("off")
            return SessionResult(detection=detection, transcript=None, dialogue=None,
                                 error="no_transcript")

        logger.info("Heard [%s/%s]: %s", transcript.language, transcript.age_hint, transcript.text)

        # Step 3: retrieve context (Phase 2 bridge)
        chunks = self._retriever(detection.artwork_id, transcript.text)
        if not chunks:
            logger.warning("Retriever returned no chunks for artwork_id=%s", detection.artwork_id)

        # Step 4: generate dialogue response (Phase 3)
        dialogue_result = self._engine.respond(
            question=transcript.text,
            artwork_chunks=chunks,
            language=transcript.language,
            visitor_age=_age_hint_to_number(transcript.age_hint),
        )

        logger.info(
            "Response [grounded=%s filtered=%s]: %.80s...",
            dialogue_result.grounded,
            dialogue_result.filtered,
            dialogue_result.response,
        )

        # Step 5: speak the answer. TTS failure is non-fatal — the answer
        # text is still returned so the dashboard can display it.
        self._hw.set_status_led("green")
        spoke = self._tts.speak(dialogue_result.response, language=transcript.language)
        if not spoke:
            logger.warning("tts_fallback_used: showing answer as text only")

        # Step 6: signal EV3 stand
        self._hw.send(StandCommand.ROTATE_CW, stand_id=1)
        self._hw.set_status_led("off")

        return SessionResult(
            detection=detection,
            transcript=transcript,
            dialogue=dialogue_result,
            tts_ok=bool(spoke),
        )
