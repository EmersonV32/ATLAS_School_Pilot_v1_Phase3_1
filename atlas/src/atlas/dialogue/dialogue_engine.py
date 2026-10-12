"""DialogueEngine: the main orchestrator for Phase 3.

Pipeline:
    question + chunks
        → PromptBuilder         (assemble messages)
        → LLM client            (MockLLMClient in dev, GeminiClient in device/demo)
        → GroundingValidator    (token-overlap heuristic)
        → SafetyFilter          (block inappropriate content)
        → DialogueResult

Usage example (dev mode):
    from atlas.dialogue.mock_llm_client import MockLLMClient
    from atlas.dialogue.dialogue_engine import DialogueEngine

    engine = DialogueEngine(llm_client=MockLLMClient())
    result = engine.respond(
        question="Who painted this?",
        artwork_chunks=[
            {"text": "The Starry Night was painted by Vincent van Gogh in 1889."}
        ],
        language="en",
    )
    print(result.response)
"""

from __future__ import annotations

import json
import logging
import queue
import re
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from atlas.dialogue.conversation_memory import ArtworkFocus, ConversationMemory
from atlas.dialogue.grounding_validator import GroundingValidator
from atlas.dialogue.personalization import SessionPersonalization
from atlas.dialogue.prompt_builder import (
    DialogueContext,
    PromptBuilder,
    _extract_chunk_id,
)
from atlas.dialogue.safety_filter import SafetyFilter
from atlas.dialogue.sentence_stream import SentenceAssembler
from atlas.safety.prompt_injection_filter import PromptInjectionFilter

logger = logging.getLogger(__name__)

# Retained only for backwards compatibility with older integrations. RAG is
# supporting context, never a gate that suppresses Gemini's normal knowledge.
UNGROUNDED_FALLBACK = {
    "en": (
        "I don't have that detail verified in my guide yet, but I can tell "
        "you what is confirmed about this artwork."
    ),
    "fr": (
        "Je n'ai pas encore cette information vérifiée dans mon guide, mais "
        "je peux expliquer ce qui est confirmé sur cette œuvre."
    ),
    "es": (
        "Todavía no tengo ese detalle verificado en mi guía, pero puedo "
        "explicarte lo que está confirmado sobre esta obra."
    ),
    "it": (
        "Non ho ancora quel dettaglio verificato nella mia guida, ma posso "
        "spiegarti ciò che è confermato su quest'opera."
    ),
}

LLM_ERROR_FALLBACK = {
    "en": "I'm sorry, I can't generate a response right now.",
    "fr": "Je suis désolé, je ne peux pas répondre en ce moment.",
    "es": "Lo siento, no puedo generar una respuesta en este momento.",
    "it": "Mi dispiace, non posso generare una risposta in questo momento.",
}


@dataclass
class DialogueResult:
    response: str
    language: str
    grounded: bool
    grounding_reason: str
    filtered: bool
    error: str | None = None
    used_chunk_ids: list[str] = field(default_factory=list)
    confidence: str = "medium"  # high | medium | low
    fallback_used: bool = False


def _parse_structured(raw: str) -> dict | None:
    """Parse the LLM JSON contract if present; None means plain text.

    Accepts bare JSON or JSON inside a ```json fence. Requires a non-empty
    spoken_answer to count as structured output.
    """
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    spoken = data.get("spoken_answer")
    if not isinstance(spoken, str) or not spoken.strip():
        return None
    return data


class DialogueEngine:
    """
    Orchestrates prompt building, LLM generation, grounding validation,
    and safety filtering for a single visitor question.

    The llm_client is injected — pass MockLLMClient for dev/test,
    GeminiClient for device/demo modes.
    """

    def __init__(
        self,
        llm_client,
        expect_json: bool = False,
        artwork_titles: dict[str, str] | None = None,
    ) -> None:
        self._llm = llm_client
        self._expect_json = expect_json  # True for real LLMs (Gemini)
        self._prompt_builder = PromptBuilder()
        self._validator = GroundingValidator()
        self._safety = SafetyFilter()
        self._injection = PromptInjectionFilter()
        self._conversation_turns: list[tuple[str, str]] = []
        self._memory = ConversationMemory(artwork_titles)
        self._personalization = SessionPersonalization()
        self._state_lock = threading.RLock()
        self._conversation_generation = 0

    @property
    def conversation_generation(self) -> int:
        with self._state_lock:
            return self._conversation_generation

    def _cancelled(self, language: str) -> DialogueResult:
        return DialogueResult(
            response="",
            language=language,
            grounded=False,
            grounding_reason="session_cancelled",
            filtered=False,
            error="session_cancelled",
        )

    def prepare_turn(
        self,
        question: str,
        artwork_id: str | None,
        *,
        expected_generation: int | None = None,
        force_camera: bool = False,
    ) -> ArtworkFocus | None:
        """Resolve one shared subject before either local FAQ or RAG selection."""
        with self._state_lock:
            generation = self._conversation_generation
            if expected_generation is not None and generation != expected_generation:
                return None
            safe_question = "" if self._injection.is_injection(question) else question
            return self._memory.focus(
                safe_question, artwork_id, generation, force_camera=force_camera
            )

    def _context(
        self,
        *,
        expected_generation: int | None,
        focus: ArtworkFocus | None = None,
        **kwargs,
    ):
        """Snapshot one session without holding a lock during cloud calls."""
        with self._state_lock:
            generation = self._conversation_generation
            if expected_generation is not None and generation != expected_generation:
                return generation, None
            focus = focus or self._memory.focus(
                ""
                if self._injection.is_injection(kwargs["question"])
                else kwargs["question"],
                kwargs.get("artwork_id"),
                generation,
            )
            if focus.generation != generation:
                return generation, None
            self._personalization.observe(kwargs["question"])
            interests, styles = self._personalization.prompt_lines()
            return generation, DialogueContext(
                **kwargs,
                conversation_turns=list(self._conversation_turns),
                conversation_artwork_ids=[t.artwork_id for t in self._memory.recent],
                topic_artwork_id=focus.artwork_id,
                named_artwork_ids=focus.named_ids,
                artwork_transition=focus.transition,
                earlier_conversation=self._memory.earlier_context(focus),
                visitor_interests=interests,
                explanation_preferences=styles,
                ask_preference_question=self._personalization.should_ask_preference_question(),
            )

    def _commit_turn(
        self,
        generation: int,
        question: str,
        result: DialogueResult,
        ask: bool,
        artwork_id: str | None = None,
    ):
        with self._state_lock:
            if generation != self._conversation_generation:
                return self._cancelled(result.language)
            if not result.error and not result.filtered:
                self._remember(question, result.response, artwork_id)
            self._personalization.complete_turn(preference_question_requested=ask)
            return result

    def reset_conversation(self) -> None:
        """Clear privacy-bounded in-memory context at a session boundary."""
        with self._state_lock:
            self._conversation_generation += 1
            self._conversation_turns.clear()
            self._memory.reset()
            self._personalization.reset()

    def configure_personalization(
        self,
        *,
        interests: list[str] | None = None,
        accessibility: list[str] | None = None,
        expertise: str | None = None,
    ) -> None:
        """Start a session with only coarse, allow-listed visitor choices."""
        with self._state_lock:
            self._personalization.configure(
                interests=interests,
                accessibility=accessibility,
                expertise=expertise,
            )

    def _remember(
        self, question: str, answer: str, artwork_id: str | None = None
    ) -> None:
        self._memory.remember(question, answer, artwork_id)
        self._conversation_turns = [(t.question, t.answer) for t in self._memory.recent]

    def remember_local_response(
        self,
        question: str,
        answer: str,
        *,
        expected_generation: int | None = None,
        artwork_id: str | None = None,
        focus: ArtworkFocus | None = None,
    ) -> bool:
        """Keep a deterministic local answer in the same visit-only memory."""
        with self._state_lock:
            if (
                expected_generation is not None
                and expected_generation != self._conversation_generation
            ):
                return False
            focus = focus or self._memory.focus(
                question, artwork_id, self._conversation_generation
            )
            if focus.generation != self._conversation_generation:
                return False
            self._personalization.observe(question)
            self._remember(question, answer, focus.artwork_id)
            self._personalization.complete_turn(preference_question_requested=False)
            return True

    def respond(
        self,
        question: str,
        artwork_chunks: list,
        visitor_age: int | None = None,
        language: str = "en",
        profile: str | None = None,
        artwork_id: str | None = None,
        expected_generation: int | None = None,
        focus: ArtworkFocus | None = None,
    ) -> DialogueResult:
        generation, ctx = self._context(
            expected_generation=expected_generation,
            focus=focus,
            question=question,
            artwork_chunks=artwork_chunks,
            visitor_age=visitor_age,
            visitor_language=language,
            profile=profile,
            artwork_id=artwork_id,
        )
        if ctx is None:
            return self._cancelled(language)
        # 0. Prompt-injection guard — refuse before any LLM call.
        if self._injection.is_injection(question):
            logger.warning("Prompt injection detected — refusing safely.")
            return DialogueResult(
                response=self._injection.safe_response(language),
                language=language,
                grounded=True,
                grounding_reason="injection_refused",
                filtered=True,
                fallback_used=True,
                confidence="high",
            )

        # 1. Learn only allow-listed preferences locally, then build one prompt.
        messages = self._prompt_builder.build(ctx, json_output=self._expect_json)

        # 2. Call LLM
        raw_response: str
        try:
            raw_response = self._llm.generate(messages)
        except Exception as exc:  # pylint: disable=broad-except
            if generation != self.conversation_generation:
                return self._cancelled(language)
            logger.error("LLM generation failed: %s", exc)
            fallback = LLM_ERROR_FALLBACK.get(language, LLM_ERROR_FALLBACK["en"])
            return DialogueResult(
                response=fallback,
                language=language,
                grounded=False,
                grounding_reason="llm_error",
                filtered=False,
                error=str(exc),
                fallback_used=True,
                confidence="low",
            )

        # 2b. Parse the structured JSON contract when present. Plain text
        # (e.g. from MockLLMClient) is used as the spoken answer directly.
        spoken = raw_response
        used_chunk_ids: list[str] = []
        confidence = "medium"
        unsupported_claims: list = []
        structured = _parse_structured(raw_response)
        if structured is not None:
            spoken = structured["spoken_answer"].strip()
            confidence = str(structured.get("confidence", "medium"))
            claims = structured.get("unsupported_claims")
            unsupported_claims = claims if isinstance(claims, list) else []
            # used_chunk_ids must refer to chunks we actually retrieved.
            known_ids = {
                cid for cid in (_extract_chunk_id(c) for c in artwork_chunks) if cid
            }
            raw_ids = structured.get("used_chunk_ids") or []
            if isinstance(raw_ids, list):
                used_chunk_ids = [str(i) for i in raw_ids if str(i) in known_ids]
                invalid = [str(i) for i in raw_ids if str(i) not in known_ids]
                if invalid:
                    logger.warning("LLM cited unknown chunk ids: %s", invalid)

        # 3. Record retrieval overlap for observability only. A mismatch must
        # never replace a useful Gemini answer with a database-style refusal.
        is_grounded, grounding_reason = self._validator.validate(spoken, artwork_chunks)
        if unsupported_claims:
            is_grounded = False
            grounding_reason = "unsupported_claims"
        fallback_used = bool(structured and structured.get("fallback_used"))
        if not is_grounded:
            logger.warning(
                "Grounding check did not match retrieved context (%s); "
                "retaining Gemini answer.",
                grounding_reason,
            )
            fallback_used = False

        # 4. Safety filter (always speaks last).
        final_response, was_filtered = self._safety.filter(spoken, language)
        if was_filtered:
            logger.warning("Response was blocked by safety filter.")

        result = DialogueResult(
            response=final_response,
            language=language,
            grounded=is_grounded,
            grounding_reason=grounding_reason,
            filtered=was_filtered,
            used_chunk_ids=used_chunk_ids,
            confidence=confidence,
            fallback_used=fallback_used,
        )
        return self._commit_turn(
            generation,
            question,
            result,
            ctx.ask_preference_question,
            ctx.topic_artwork_id,
        )

    def respond_stream(
        self,
        question: str,
        artwork_chunks: list,
        on_sentence: Callable[[str], object],
        visitor_age: int | None = None,
        language: str = "en",
        profile: str | None = None,
        artwork_id: str | None = None,
        expected_generation: int | None = None,
        focus: ArtworkFocus | None = None,
    ) -> DialogueResult:
        """Generate and validate in one thread while TTS consumes sentences.

        The producer continues pulling LLM tokens while ``on_sentence`` plays
        the previous sentence, hiding most TTS time without speaking an
        unvalidated sentence.
        """
        generation, ctx = self._context(
            expected_generation=expected_generation,
            focus=focus,
            question=question,
            artwork_chunks=artwork_chunks,
            visitor_age=visitor_age,
            visitor_language=language,
            profile=profile,
            artwork_id=artwork_id,
        )
        if ctx is None:
            return self._cancelled(language)
        if self._injection.is_injection(question):
            result = DialogueResult(
                response=self._injection.safe_response(language),
                language=language,
                grounded=True,
                grounding_reason="injection_refused",
                filtered=True,
                fallback_used=True,
                confidence="high",
            )
            if generation != self.conversation_generation:
                return self._cancelled(language)
            on_sentence(result.response)
            return result

        messages = self._prompt_builder.build(ctx, streaming_output=True)
        events: queue.Queue[tuple[str, object]] = queue.Queue()

        def generate_chunks() -> Iterable[str]:
            stream_method = getattr(self._llm, "generate_stream", None)
            if callable(stream_method):
                return stream_method(messages)
            return (self._llm.generate(messages),)

        def producer() -> None:
            assembler = SentenceAssembler()
            accepted: list[str] = []
            grounded = True
            grounding_reason = "stream_complete"
            filtered = False
            fallback_used = False
            error: str | None = None
            try:
                for text_chunk in generate_chunks():
                    if generation != self.conversation_generation:
                        events.put(("done", self._cancelled(language)))
                        return
                    for sentence in assembler.feed(text_chunk):
                        ok, reason = self._validator.validate(
                            sentence,
                            artwork_chunks,
                        )
                        if not ok:
                            grounded = False
                            grounding_reason = reason
                            logger.warning(
                                "Streaming sentence does not overlap retrieved context "
                                "(%s); retaining Gemini sentence.",
                                reason,
                            )
                        sentence, was_filtered = self._safety.filter(
                            sentence,
                            language,
                        )
                        filtered = filtered or was_filtered
                        accepted.append(sentence)
                        events.put(("sentence", sentence))
                        if was_filtered:
                            raise StopIteration

                remainder = assembler.flush()
                if remainder:
                    ok, reason = self._validator.validate(remainder, artwork_chunks)
                    if not ok:
                        grounded = False
                        grounding_reason = reason
                        logger.warning(
                            "Streaming remainder does not overlap retrieved context "
                            "(%s); retaining Gemini answer.",
                            reason,
                        )
                    remainder, was_filtered = self._safety.filter(
                        remainder,
                        language,
                    )
                    filtered = filtered or was_filtered
                    accepted.append(remainder)
                    events.put(("sentence", remainder))
            except StopIteration:
                pass
            except Exception as exc:
                logger.error("Streaming LLM generation failed: %s", exc)
                error = str(exc)
                grounded = False
                grounding_reason = "llm_error"
                if not accepted:
                    fallback_used = True
                    fallback = LLM_ERROR_FALLBACK.get(
                        language, LLM_ERROR_FALLBACK["en"]
                    )
                    accepted.append(fallback)
                    events.put(("sentence", fallback))

            result = DialogueResult(
                response=" ".join(accepted).strip(),
                language=language,
                grounded=grounded,
                grounding_reason=grounding_reason,
                filtered=filtered,
                error=error,
                confidence="medium" if grounded else "low",
                fallback_used=fallback_used,
            )
            events.put(
                (
                    "done",
                    self._commit_turn(
                        generation,
                        question,
                        result,
                        ctx.ask_preference_question,
                        ctx.topic_artwork_id,
                    ),
                )
            )

        thread = threading.Thread(
            target=producer,
            name="atlas-llm-stream",
            daemon=True,
        )
        thread.start()
        while True:
            if generation != self.conversation_generation:
                return self._cancelled(language)
            try:
                event_type, payload = events.get(timeout=0.1)
            except queue.Empty:
                continue
            if generation != self.conversation_generation:
                return self._cancelled(language)
            if event_type == "sentence":
                on_sentence(str(payload))
                continue
            thread.join(timeout=0.2)
            return payload
