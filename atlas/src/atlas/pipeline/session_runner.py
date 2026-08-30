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
import re
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from atlas.audio.stt import BaseSTT, TranscriptResult
from atlas.audio.tts import BaseTTS
from atlas.dialogue.dialogue_engine import DialogueEngine, DialogueResult
from atlas.hardware.base import BaseHardware
from atlas.models.languages import normalize_language_code
from atlas.vision.detector import ArtworkDetection, BaseDetector
from atlas.vision.manual_capture import is_capture_command

logger = logging.getLogger(__name__)


def _age_hint_to_number(age_hint):
    mapping = {"child": 8, "teen": 14, "adult": 30}
    if isinstance(age_hint, int):
        return age_hint
    return mapping.get(str(age_hint).lower())


def _format_optional_ms(value) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.0f}"


RetrieverFn = Callable[[str | None, str], list[dict]]

_CAPTURE_CONFIRMATIONS = {
    "en": "I captured this as {title}. What would you like to know?",
    "zh": "我已將這件作品辨識為 {title}。您想了解什麼？",
    "hi": "मैंने इसे {title} के रूप में पहचाना है। आप क्या जानना चाहेंगे?",
    "es": "Identifiqué esta obra como {title}. ¿Qué le gustaría saber?",
    "fr": "J'ai identifié cette œuvre comme {title}. Que voulez-vous savoir?",
    "ar": "تعرّفت على هذا العمل على أنه {title}. ماذا تود أن تعرف؟",
    "bn": "আমি এটিকে {title} হিসেবে শনাক্ত করেছি। আপনি কী জানতে চান?",
    "pt": "Identifiquei esta obra como {title}. O que gostaria de saber?",
    "ru": "Я распознал это произведение как {title}. Что вы хотели бы узнать?",
    "id": "Saya mengenali karya ini sebagai {title}. Apa yang ingin Anda ketahui?",
    "de": "Ich habe dieses Werk als {title} erkannt. Was möchten Sie wissen?",
    "ja": "この作品は{title}です。何を知りたいですか？",
    "te": "నేను ఈ కళాఖండాన్ని {title}గా గుర్తించాను. మీరు ఏమి తెలుసుకోవాలనుకుంటున్నారు?",
    "tr": "Bu eseri {title} olarak tanıdım. Ne öğrenmek istersiniz?",
    "ko": "이 작품은 {title}입니다. 무엇이 궁금하신가요?",
    "vi": "Tôi nhận diện tác phẩm này là {title}. Bạn muốn biết điều gì?",
    "it": "Ho identificato quest'opera come {title}. Cosa vorrebbe sapere?",
    "ta": (
        "இந்தக் கலைப்படைப்பை {title} என அடையாளம் கண்டேன். "
        "நீங்கள் என்ன தெரிந்துகொள்ள விரும்புகிறீர்கள்?"
    ),
    "th": "ฉันระบุผลงานนี้ว่าเป็น {title} คุณอยากรู้อะไรเพิ่มเติม?",
    "pl": "Rozpoznałem to dzieło jako {title}. Co chcesz wiedzieć?",
}

_CAPTURE_FAILURES = {
    "en": "I could not identify that artwork. Please center it and try again.",
    "zh": "我無法辨識這件作品。請將作品置中後再試一次。",
    "hi": "मैं उस कलाकृति को पहचान नहीं सका। उसे बीच में रखें और फिर प्रयास करें।",
    "es": "No pude identificar la obra. Céntrela e inténtelo de nuevo.",
    "fr": "Je n'ai pas pu identifier cette œuvre. Centrez-la et réessayez.",
    "ar": "لم أتمكن من التعرف على العمل. ضعه في المنتصف وحاول مرة أخرى.",
    "bn": "আমি শিল্পকর্মটি শনাক্ত করতে পারিনি। এটিকে মাঝখানে রেখে আবার চেষ্টা করুন।",
    "pt": "Não consegui identificar a obra. Centralize-a e tente novamente.",
    "ru": (
        "Не удалось распознать произведение. "
        "Поместите его в центр и попробуйте снова."
    ),
    "id": "Saya tidak dapat mengenali karya itu. Posisikan di tengah lalu coba lagi.",
    "de": (
        "Ich konnte das Werk nicht erkennen. "
        "Zentrieren Sie es und versuchen Sie es erneut."
    ),
    "ja": "作品を特定できませんでした。中央に合わせて、もう一度お試しください。",
    "te": "ఆ కళాఖండాన్ని గుర్తించలేకపోయాను. దాన్ని మధ్యలో ఉంచి మళ్లీ ప్రయత్నించండి.",
    "tr": "Eseri tanıyamadım. Ortalayın ve yeniden deneyin.",
    "ko": "작품을 식별하지 못했습니다. 중앙에 맞추고 다시 시도해 주세요.",
    "vi": "Tôi không thể nhận diện tác phẩm. Hãy đặt nó ở giữa rồi thử lại.",
    "it": "Non ho riconosciuto l'opera. La centri e riprovi.",
    "ta": "அந்தக் கலைப்படைப்பை அடையாளம் காண முடியவில்லை. அதை நடுவில் வைத்து மீண்டும் முயற்சிக்கவும்.",
    "th": "ฉันไม่สามารถระบุผลงานได้ กรุณาจัดให้อยู่ตรงกลางแล้วลองอีกครั้ง",
    "pl": "Nie udało mi się rozpoznać dzieła. Ustaw je na środku i spróbuj ponownie.",
}

_ARTWORK_INVITATIONS = {
    "en": "Would you like to know more about {title}?",
    "zh": "您想進一步了解{title}嗎？",
    "hi": "क्या आप {title} के बारे में और जानना चाहेंगे?",
    "es": "¿Le gustaría saber más sobre {title}?",
    "fr": "Voulez-vous en savoir plus sur {title} ?",
    "ar": "هل تود معرفة المزيد عن {title}؟",
    "bn": "আপনি কি {title} সম্পর্কে আরও জানতে চান?",
    "pt": "Gostaria de saber mais sobre {title}?",
    "ru": "Хотите узнать больше о {title}?",
    "id": "Apakah Anda ingin tahu lebih banyak tentang {title}?",
    "de": "Möchten Sie mehr über {title} erfahren?",
    "ja": "{title}についてもっと知りたいですか？",
    "te": "మీరు {title} గురించి మరింత తెలుసుకోవాలనుకుంటున్నారా?",
    "tr": "{title} hakkında daha fazla bilgi ister misiniz?",
    "ko": "{title}에 대해 더 알고 싶으신가요?",
    "vi": "Bạn có muốn biết thêm về {title} không?",
    "it": "Vuole saperne di più su {title}?",
    "ta": "{title} பற்றி மேலும் தெரிந்துகொள்ள விரும்புகிறீர்களா?",
    "th": "คุณอยากทราบข้อมูลเพิ่มเติมเกี่ยวกับ {title} ไหม?",
    "pl": "Czy chcesz dowiedzieć się więcej o {title}?",
}

_LANGUAGE_ACKNOWLEDGEMENTS = {
    "en": "Okay, I will continue in English.",
    "zh": "好的，我会继续用中文。",
    "hi": "ठीक है, मैं हिंदी में जारी रखूँगा।",
    "es": "De acuerdo, continuare en espanol.",
    "fr": "D'accord, je continue en francais.",
    "ar": "حسنًا، سأتابع باللغة العربية.",
    "bn": "ঠিক আছে, আমি বাংলায় কথা চালিয়ে যাব।",
    "pt": "Certo, vou continuar em português.",
    "ru": "Хорошо, я продолжу на русском языке.",
    "id": "Baik, saya akan melanjutkan dalam bahasa Indonesia.",
    "de": "In Ordnung, ich spreche auf Deutsch weiter.",
    "ja": "わかりました。日本語で続けます。",
    "te": "సరే, నేను తెలుగులో కొనసాగిస్తాను.",
    "tr": "Tamam, Türkçe devam edeceğim.",
    "ko": "알겠습니다. 한국어로 계속하겠습니다.",
    "vi": "Được, tôi sẽ tiếp tục bằng tiếng Việt.",
    "it": "Va bene, continuero in italiano.",
    "ta": "சரி, நான் தமிழில் தொடர்கிறேன்.",
    "th": "ตกลง ฉันจะพูดภาษาไทยต่อ",
    "pl": "Dobrze, będę kontynuować po polsku.",
}

_LANGUAGE_NAMES = {
    "en": {"english", "anglais", "ingles", "inglese"},
    "zh": {"chinese", "mandarin"},
    "hi": {"hindi"},
    "es": {"spanish", "espagnol", "espanol", "spagnolo"},
    "fr": {"french", "francais", "frances", "francese"},
    "ar": {"arabic"},
    "bn": {"bengali", "bangla"},
    "pt": {"portuguese", "portugues"},
    "ru": {"russian"},
    "id": {"indonesian", "bahasa"},
    "de": {"german", "deutsch"},
    "ja": {"japanese"},
    "te": {"telugu"},
    "tr": {"turkish"},
    "ko": {"korean"},
    "vi": {"vietnamese"},
    "it": {"italian", "italien", "italiano"},
    "ta": {"tamil"},
    "th": {"thai"},
    "pl": {"polish"},
}

_LANGUAGE_SWITCH_WORDS = {
    "switch", "change", "speak", "talk", "continue", "answer", "respond",
    "return", "back", "go", "parle", "parles", "parler", "parlez",
    "passe", "passez", "passer", "changez", "changer", "continues",
    "continuez", "continuer", "reponds", "repondez", "repondre", "retour",
    "reviens", "habla", "hablar", "hable", "cambia", "cambiar", "cambie",
    "continua", "continuar", "responde", "responder", "parla", "parlare",
    "cambiare", "continuare", "rispondi", "rispondere",
}

_LANGUAGE_QUESTION_WORDS = {
    "who", "what", "when", "where", "why", "which", "qui", "que",
    "quand", "ou", "pourquoi", "quel", "quelle", "quien", "cuando",
    "donde", "por", "cual", "chi", "cosa", "quando", "dove", "perche",
    "quale",
}

_DEICTIC_ARTWORK_REFERENCE = re.compile(
    r"\b(?:it|this|that|one|ceci|cela|ca|cette|esta|esto|questa|questo)\b",
    re.IGNORECASE,
)


def requested_language(text: str) -> str | None:
    """Return a direct spoken language-switch target, without using the LLM."""
    normalized = unicodedata.normalize("NFKD", str(text).casefold())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    words = re.findall(r"[a-z]+", normalized)
    for index, word in enumerate(words):
        if word not in _LANGUAGE_SWITCH_WORDS:
            continue
        if words and words[0] in _LANGUAGE_QUESTION_WORDS:
            return None
        remaining = set(words[index + 1 :])
        for language, names in _LANGUAGE_NAMES.items():
            if remaining.intersection(names):
                return language
    return None


def _needs_identified_artwork(query: str) -> bool:
    """Return True when a deictic question has no named artwork to resolve it."""
    normalized = unicodedata.normalize("NFKD", str(query).casefold())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return bool(_DEICTIC_ARTWORK_REFERENCE.search(normalized))


@dataclass
class SessionResult:
    detection: ArtworkDetection | None
    transcript: TranscriptResult | None
    dialogue: DialogueResult | None
    error: str | None = None
    tts_ok: bool = True  # False = tts_fallback_used (answer shown as text)
    event: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None and (
            self.dialogue is not None or self.event is not None
        )


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
    from atlas.models.enums import Language
    from atlas.rag.retriever import RetrievalQuery

    def _lang(code: str) -> Language:
        return Language(normalize_language_code(code))

    def _retrieve(
        artwork_id: str | None,
        query: str,
        language: str = "en",
    ) -> list[dict]:
        # Never let a collection-wide search turn "Who created it?" into an
        # answer about an arbitrary high-ranking artwork. The dialogue prompt
        # will ask for the artwork when vision has not identified one.
        if artwork_id is None and _needs_identified_artwork(query):
            logger.info("[RAG] Skipped ambiguous deictic query without artwork context")
            return []
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
        stream_responses: bool = False,
        manual_capture=None,
        log_transcripts: bool = False,
        log_llm_responses: bool = False,
    ) -> None:
        self._detector = detector
        self._stt = stt
        self._tts = tts
        self._hw = hardware
        self._engine = dialogue_engine
        self._retriever = retriever
        self._listen_s = listen_duration_s
        self._stream_responses = stream_responses
        self._manual_capture = manual_capture
        self._log_transcripts = log_transcripts
        self._log_llm_responses = log_llm_responses
        self._last_language = "en"
        self._preferred_language = "en"
        self._preferred_profile = "adult_beginner"

    def set_preferred_language(self, language: str) -> None:
        normalized = normalize_language_code(language)
        self._preferred_language = normalized
        self._last_language = normalized

    def set_preferred_profile(self, profile: str) -> None:
        """Apply the privacy-bounded dashboard profile to spoken answers."""
        allowed = {
            "child",
            "teen",
            "adult_beginner",
            "expert",
            "visual_impairment",
            "simple_language",
        }
        self._preferred_profile = (
            str(profile) if str(profile) in allowed else "adult_beginner"
        )

    @property
    def preferred_language(self) -> str:
        return self._preferred_language

    @property
    def preferred_profile(self) -> str:
        return self._preferred_profile

    def _listen(self, *, play_cue: bool = True) -> TranscriptResult | None:
        listen_started = time.perf_counter()
        logger.info(
            "[STT] Preparing to listen [language=%s timeout=%.1fs]",
            self._preferred_language,
            self._listen_s,
        )
        set_language = getattr(self._stt, "set_language", None)
        if callable(set_language):
            set_language(self._preferred_language)
        try:
            self._stt.prepare_listen()
        except Exception as exc:
            logger.warning(
                "[STT] Preparation failed; attempting listen anyway: %s",
                exc,
            )
        if play_cue:
            try:
                if not self._tts.cue():
                    logger.warning("Listening cue unavailable; recording anyway")
            except Exception as exc:
                logger.warning("[TTS] Listening cue error: %s", exc)
        try:
            transcript = self._stt.listen(duration_s=self._listen_s)
        except Exception as exc:
            logger.exception("[STT] All available transcription paths failed: %s", exc)
            logger.info(
                "[Timing] STT failed after %.0f ms",
                (time.perf_counter() - listen_started) * 1000.0,
            )
            return None
        if transcript is not None:
            switch_target = requested_language(transcript.text)
            if switch_target is not None:
                self.set_preferred_language(switch_target)
                transcript.language = switch_target
            else:
                transcript.language = self._preferred_language
            if self._log_transcripts:
                logger.info("[STT final] %s", transcript.text)
            logger.info(
                "[STT] Final result [language=%s confidence=%.2f "
                "provider_ms=%s provider=%s]",
                transcript.language,
                transcript.confidence,
                (
                    f"{transcript.duration_ms:.0f}"
                    if transcript.duration_ms is not None
                    else "n/a"
                ),
                getattr(self._stt, "last_provider", type(self._stt).__name__),
            )
        else:
            logger.info("[STT] No transcript returned")
        logger.info(
            "[Timing] STT total %.0f ms",
            (time.perf_counter() - listen_started) * 1000.0,
        )
        return transcript

    def cue_listening(self) -> None:
        """Play one cue when a continuous listening session becomes active."""
        try:
            if not self._tts.cue():
                logger.warning("Listening cue unavailable; listening anyway")
        except Exception as exc:
            logger.warning("[TTS] Listening cue error: %s", exc)

    def listen_once(self, *, play_cue: bool = False) -> TranscriptResult | None:
        """Capture one utterance without coupling it to artwork detection."""
        return self._listen(play_cue=play_cue)

    def _speak_capture_message(
        self,
        detection: ArtworkDetection | None,
        language: str,
    ) -> None:
        language = normalize_language_code(language)
        if detection is None:
            message = _CAPTURE_FAILURES[language]
        else:
            message = _CAPTURE_CONFIRMATIONS[language].format(title=detection.label)
        logger.info("[TTS message] %s", message)
        try:
            self._tts.speak(message, language=language)
        except Exception as exc:
            logger.warning("Manual capture announcement failed: %s", exc)

    def invite_about_artwork(
        self,
        detection: ArtworkDetection,
        language: str | None = None,
    ) -> bool:
        """Offer a localized follow-up without opening another listen cycle."""
        selected_language = normalize_language_code(
            language or self._preferred_language
        )
        message = _ARTWORK_INVITATIONS[selected_language].format(
            title=detection.label
        )
        self._hw.focus_artwork(detection.artwork_id)
        self._hw.set_status_led("amber")
        logger.info(
            "[Demo] Inviting artwork follow-up [artwork_id=%s language=%s]",
            detection.artwork_id,
            selected_language,
        )
        try:
            return bool(self._tts.speak(message, language=selected_language))
        except Exception as exc:
            logger.warning("Artwork invitation failed: %s", exc)
            return False
        finally:
            self._hw.set_status_led("off")

    def _identify_manually(self, frame: Any) -> ArtworkDetection | None:
        if self._manual_capture is None:
            logger.warning("Manual artwork capture is unavailable")
            return None
        try:
            return self._manual_capture.identify(frame)
        except Exception as exc:
            logger.warning("Manual artwork capture failed: %s", exc)
            return None

    def run_manual_capture(self, frame: Any) -> SessionResult:
        """Identify the center crop first, then run a normal question cycle."""
        detection = self._identify_manually(frame)
        if detection is None:
            self._speak_capture_message(None, self._last_language)
            return SessionResult(
                detection=None,
                transcript=None,
                dialogue=None,
                error="manual_capture_unknown",
            )
        return self.run_once(frame=frame, detection_override=detection)

    def run_once(
        self,
        frame: Any = None,
        detection_override: ArtworkDetection | None = None,
    ) -> SessionResult:
        """Run one full cycle. frame can be a camera frame or None (mock)."""

        cycle_started = time.perf_counter()

        # Step 1: detect artwork
        detection = detection_override or self._detector.detect(frame)
        if detection is None:
            logger.debug("No artwork detected — skipping cycle.")
            return SessionResult(
                detection=None, transcript=None, dialogue=None, error="no_detection"
            )

        logger.info(
            "[Vision] Detected %s [artwork_id=%s confidence=%.0f%% "
            "source=%s center=%s]",
            detection.label,
            detection.artwork_id,
            detection.confidence * 100,
            detection.source,
            (
                f"{detection.center_score:.2f}"
                if detection.center_score is not None
                else "n/a"
            ),
        )
        self._hw.focus_artwork(detection.artwork_id)
        self._hw.set_status_led("amber")

        if detection.source == "manual_capture":
            self._speak_capture_message(detection, self._last_language)

        # Step 2: listen for visitor question
        transcript = self._listen()
        if transcript is None or not transcript.text.strip():
            logger.warning(
                "[Cycle] Stopped: no_transcript [total_ms=%.0f]",
                (time.perf_counter() - cycle_started) * 1000.0,
            )
            self._hw.set_status_led("off")
            self._hw.reset_exhibit()
            return SessionResult(
                detection=detection,
                transcript=None,
                dialogue=None,
                error="no_transcript",
            )

        self._last_language = transcript.language
        if is_capture_command(transcript.text):
            corrected_detection = self._identify_manually(frame)
            if corrected_detection is None:
                self._speak_capture_message(None, transcript.language)
                self._hw.set_status_led("off")
                self._hw.reset_exhibit()
                return SessionResult(
                    detection=detection,
                    transcript=transcript,
                    dialogue=None,
                    error="manual_capture_unknown",
                )

            detection = corrected_detection
            self._hw.focus_artwork(detection.artwork_id)
            self._speak_capture_message(detection, transcript.language)
            transcript = self._listen()
            if transcript is None or not transcript.text.strip():
                logger.warning(
                    "[Cycle] Stopped after manual capture: no_transcript "
                    "[total_ms=%.0f]",
                    (time.perf_counter() - cycle_started) * 1000.0,
                )
                self._hw.set_status_led("off")
                self._hw.reset_exhibit()
                return SessionResult(
                    detection=detection,
                    transcript=None,
                    dialogue=None,
                    error="no_transcript",
                )
            self._last_language = transcript.language

        # Step 3: retrieve context (Phase 2 bridge)
        retrieval_started = time.perf_counter()
        try:
            chunks = self._retriever(
                detection.artwork_id, transcript.text, transcript.language
            )
        except TypeError:
            chunks = self._retriever(detection.artwork_id, transcript.text)
        if not chunks:
            logger.warning(
                "Retriever returned no chunks for artwork_id=%s",
                detection.artwork_id,
            )
        logger.info(
            "[RAG] Retrieved %d chunks [ids=%s]",
            len(chunks),
            ",".join(str(chunk.get("chunk_id", "")) for chunk in chunks),
        )
        logger.info(
            "[Timing] RAG %.0f ms",
            (time.perf_counter() - retrieval_started) * 1000.0,
        )

        # Step 4: generate dialogue response (Phase 3)
        tts_results: list[bool] = []
        llm_started = time.perf_counter()
        sentence_number = 0
        continuous_tts = False

        def speak_sentence(sentence: str) -> None:
            nonlocal sentence_number
            sentence_number += 1
            if self._log_llm_responses:
                logger.info("[LLM sentence %d] %s", sentence_number, sentence)
            if sentence_number == 1:
                logger.info(
                    "[Timing] LLM first sentence %.0f ms",
                    (time.perf_counter() - llm_started) * 1000.0,
                )
            if continuous_tts:
                try:
                    queued = bool(
                        self._tts.speak_segment(
                            sentence,
                            language=transcript.language,
                        )
                    )
                    logger.info(
                        "[TTS] Sentence %d queued in continuous context [ok=%s]",
                        sentence_number,
                        queued,
                    )
                except Exception as exc:
                    logger.exception(
                        "[TTS] Sentence %d queue failed: %s",
                        sentence_number,
                        exc,
                    )
                return
            tts_started = time.perf_counter()
            try:
                spoke_sentence = bool(
                    self._tts.speak(sentence, language=transcript.language)
                )
                tts_results.append(spoke_sentence)
                logger.info(
                    "[Timing] TTS sentence %d %.0f ms "
                    "[provider=%s first_audio_ms=%s provider_total_ms=%s ok=%s]",
                    sentence_number,
                    (time.perf_counter() - tts_started) * 1000.0,
                    getattr(self._tts, "last_provider", type(self._tts).__name__),
                    _format_optional_ms(
                        getattr(self._tts, "last_first_audio_ms", None)
                    ),
                    _format_optional_ms(getattr(self._tts, "last_total_ms", None)),
                    spoke_sentence,
                )
            except Exception as exc:
                logger.exception("[TTS] Sentence %d failed: %s", sentence_number, exc)
                tts_results.append(False)

        use_streaming = self._stream_responses and hasattr(
            self._engine,
            "respond_stream",
        )
        self._hw.set_status_led("green")
        if use_streaming:
            try:
                continuous_tts = bool(
                    self._tts.begin_utterance(language=transcript.language)
                )
            except Exception as exc:
                logger.warning("[TTS] Continuous context unavailable: %s", exc)
        if use_streaming:
            try:
                dialogue_result = self._engine.respond_stream(
                    question=transcript.text,
                    artwork_chunks=chunks,
                    on_sentence=speak_sentence,
                    language=transcript.language,
                    visitor_age=_age_hint_to_number(transcript.age_hint),
                    profile=self._preferred_profile,
                    artwork_id=detection.artwork_id,
                )
            except Exception:
                if continuous_tts:
                    self._tts.abort_utterance()
                raise
        else:
            dialogue_result = self._engine.respond(
                question=transcript.text,
                artwork_chunks=chunks,
                language=transcript.language,
                visitor_age=_age_hint_to_number(transcript.age_hint),
                profile=self._preferred_profile,
                artwork_id=detection.artwork_id,
            )

        if continuous_tts:
            tts_started = time.perf_counter()
            try:
                continuous_ok = bool(self._tts.end_utterance())
            except Exception as exc:
                logger.exception("[TTS] Continuous synthesis failed: %s", exc)
                self._tts.abort_utterance()
                continuous_ok = False
            tts_results.append(continuous_ok)
            logger.info(
                "[Timing] TTS continuous %.0f ms "
                "[sentences=%d provider=%s first_audio_ms=%s "
                "provider_total_ms=%s ok=%s]",
                (time.perf_counter() - tts_started) * 1000.0,
                sentence_number,
                getattr(self._tts, "last_provider", type(self._tts).__name__),
                _format_optional_ms(
                    getattr(self._tts, "last_first_audio_ms", None)
                ),
                _format_optional_ms(getattr(self._tts, "last_total_ms", None)),
                continuous_ok,
            )
        elif use_streaming:
            # Release the one-response provider lock used by FallbackTTS when
            # continuous synthesis was unavailable.
            self._tts.end_utterance()

        logger.info(
            "Response ready [grounded=%s filtered=%s chars=%d]",
            dialogue_result.grounded,
            dialogue_result.filtered,
            len(dialogue_result.response),
        )
        if self._log_llm_responses:
            logger.info("[LLM final] %s", dialogue_result.response)
        logger.info(
            "[Timing] LLM and streamed TTS %.0f ms "
            "[grounded=%s filtered=%s fallback=%s error=%s]",
            (time.perf_counter() - llm_started) * 1000.0,
            dialogue_result.grounded,
            dialogue_result.filtered,
            dialogue_result.fallback_used,
            dialogue_result.error or "none",
        )

        # Step 5: speak the answer. TTS failure is non-fatal — the answer
        # text is still returned so the dashboard can display it.
        try:
            if not use_streaming:
                speak_sentence(dialogue_result.response)
            spoke = bool(tts_results) and all(tts_results)
            if not spoke:
                logger.warning("tts_fallback_used: showing answer as text only")
        finally:
            # Keep the selected painting up while Atlas speaks. Afterwards all
            # three return up so the exhibit is ready for the next gaze.
            self._hw.reset_exhibit()
            self._hw.set_status_led("off")

        logger.info(
            "[Timing] Cycle total %.0f ms [tts_ok=%s]",
            (time.perf_counter() - cycle_started) * 1000.0,
            spoke,
        )

        return SessionResult(
            detection=detection,
            transcript=transcript,
            dialogue=dialogue_result,
            tts_ok=bool(spoke),
        )

    def capture_context(
        self,
        frame: Any,
        language: str | None = None,
        *,
        announce: bool = True,
    ) -> SessionResult:
        """Identify an artwork without starting another microphone capture."""
        language = language or self._last_language
        detection = self._identify_manually(frame)
        if detection is None:
            if announce:
                self._speak_capture_message(None, language)
            return SessionResult(
                detection=None,
                transcript=None,
                dialogue=None,
                error="manual_capture_unknown",
            )
        self._hw.focus_artwork(detection.artwork_id)
        if announce:
            self._speak_capture_message(detection, language)
        return SessionResult(
            detection=detection,
            transcript=None,
            dialogue=None,
            event="manual_capture_complete",
        )

    def respond_to_transcript(
        self,
        transcript: TranscriptResult,
        *,
        frame: Any = None,
        detection: ArtworkDetection | None = None,
    ) -> SessionResult:
        """Answer an utterance captured independently from the vision loop."""
        cycle_started = time.perf_counter()
        self._last_language = transcript.language

        switch_target = requested_language(transcript.text)
        if switch_target is not None:
            self.set_preferred_language(switch_target)
            transcript.language = switch_target
            response = _LANGUAGE_ACKNOWLEDGEMENTS[switch_target]
            logger.info("[Language] Switched to %s by voice command", switch_target)
            self._hw.set_status_led("green")
            try:
                spoke = bool(self._tts.speak(response, language=switch_target))
            except Exception as exc:
                logger.exception("[TTS] Language acknowledgement failed: %s", exc)
                spoke = False
            finally:
                self._hw.set_status_led("off")
            return SessionResult(
                detection=detection,
                transcript=transcript,
                dialogue=DialogueResult(
                    response=response,
                    language=switch_target,
                    grounded=True,
                    grounding_reason="local_language_switch",
                    filtered=False,
                    confidence="high",
                ),
                tts_ok=spoke,
                event="language_changed",
            )

        if is_capture_command(transcript.text):
            return self.capture_context(frame, transcript.language)

        artwork_id = detection.artwork_id if detection is not None else None
        if detection is not None:
            logger.info(
                "[Vision] Context %s [artwork_id=%s confidence=%.0f%%]",
                detection.label,
                detection.artwork_id,
                detection.confidence * 100,
            )
            self._hw.focus_artwork(detection.artwork_id)
            self._hw.set_status_led("amber")
        else:
            logger.info("[Vision] No active context; searching all artworks")

        retrieval_started = time.perf_counter()
        try:
            chunks = self._retriever(artwork_id, transcript.text, transcript.language)
        except TypeError:
            chunks = self._retriever(artwork_id, transcript.text)
        if not chunks:
            logger.warning(
                "Retriever returned no chunks for artwork_id=%s",
                artwork_id or "all",
            )
        logger.info(
            "[RAG] Retrieved %d chunks [ids=%s]",
            len(chunks),
            ",".join(str(chunk.get("chunk_id", "")) for chunk in chunks),
        )
        logger.info(
            "[Timing] RAG %.0f ms",
            (time.perf_counter() - retrieval_started) * 1000.0,
        )

        tts_results: list[bool] = []
        llm_started = time.perf_counter()
        sentence_number = 0
        continuous_tts = False

        def speak_sentence(sentence: str) -> None:
            nonlocal sentence_number
            sentence_number += 1
            if self._log_llm_responses:
                logger.info("[LLM sentence %d] %s", sentence_number, sentence)
            if sentence_number == 1:
                logger.info(
                    "[Timing] LLM first sentence %.0f ms",
                    (time.perf_counter() - llm_started) * 1000.0,
                )
            if continuous_tts:
                try:
                    queued = bool(
                        self._tts.speak_segment(
                            sentence,
                            language=transcript.language,
                        )
                    )
                    logger.info(
                        "[TTS] Sentence %d queued in continuous context [ok=%s]",
                        sentence_number,
                        queued,
                    )
                except Exception as exc:
                    logger.exception(
                        "[TTS] Sentence %d queue failed: %s",
                        sentence_number,
                        exc,
                    )
                return
            tts_started = time.perf_counter()
            try:
                spoke_sentence = bool(
                    self._tts.speak(sentence, language=transcript.language)
                )
                tts_results.append(spoke_sentence)
                logger.info(
                    "[Timing] TTS sentence %d %.0f ms "
                    "[provider=%s first_audio_ms=%s provider_total_ms=%s ok=%s]",
                    sentence_number,
                    (time.perf_counter() - tts_started) * 1000.0,
                    getattr(self._tts, "last_provider", type(self._tts).__name__),
                    _format_optional_ms(
                        getattr(self._tts, "last_first_audio_ms", None)
                    ),
                    _format_optional_ms(getattr(self._tts, "last_total_ms", None)),
                    spoke_sentence,
                )
            except Exception as exc:
                logger.exception("[TTS] Sentence %d failed: %s", sentence_number, exc)
                tts_results.append(False)

        use_streaming = self._stream_responses and hasattr(
            self._engine,
            "respond_stream",
        )
        self._hw.set_status_led("green")
        if use_streaming:
            try:
                continuous_tts = bool(
                    self._tts.begin_utterance(language=transcript.language)
                )
            except Exception as exc:
                logger.warning("[TTS] Continuous context unavailable: %s", exc)
        if use_streaming:
            try:
                dialogue_result = self._engine.respond_stream(
                    question=transcript.text,
                    artwork_chunks=chunks,
                    on_sentence=speak_sentence,
                    language=transcript.language,
                    visitor_age=_age_hint_to_number(transcript.age_hint),
                    profile=self._preferred_profile,
                    artwork_id=artwork_id,
                )
            except Exception:
                if continuous_tts:
                    self._tts.abort_utterance()
                raise
        else:
            dialogue_result = self._engine.respond(
                question=transcript.text,
                artwork_chunks=chunks,
                language=transcript.language,
                visitor_age=_age_hint_to_number(transcript.age_hint),
                profile=self._preferred_profile,
                artwork_id=artwork_id,
            )

        if continuous_tts:
            tts_started = time.perf_counter()
            try:
                continuous_ok = bool(self._tts.end_utterance())
            except Exception as exc:
                logger.exception("[TTS] Continuous synthesis failed: %s", exc)
                self._tts.abort_utterance()
                continuous_ok = False
            tts_results.append(continuous_ok)
            logger.info(
                "[Timing] TTS continuous %.0f ms "
                "[sentences=%d provider=%s first_audio_ms=%s "
                "provider_total_ms=%s ok=%s]",
                (time.perf_counter() - tts_started) * 1000.0,
                sentence_number,
                getattr(self._tts, "last_provider", type(self._tts).__name__),
                _format_optional_ms(
                    getattr(self._tts, "last_first_audio_ms", None)
                ),
                _format_optional_ms(getattr(self._tts, "last_total_ms", None)),
                continuous_ok,
            )
        elif use_streaming:
            # Release the one-response provider lock used by FallbackTTS when
            # continuous synthesis was unavailable.
            self._tts.end_utterance()

        logger.info(
            "Response ready [grounded=%s filtered=%s chars=%d]",
            dialogue_result.grounded,
            dialogue_result.filtered,
            len(dialogue_result.response),
        )
        if self._log_llm_responses:
            logger.info("[LLM final] %s", dialogue_result.response)
        logger.info(
            "[Timing] LLM and streamed TTS %.0f ms "
            "[grounded=%s filtered=%s fallback=%s error=%s]",
            (time.perf_counter() - llm_started) * 1000.0,
            dialogue_result.grounded,
            dialogue_result.filtered,
            dialogue_result.fallback_used,
            dialogue_result.error or "none",
        )

        try:
            if not use_streaming:
                speak_sentence(dialogue_result.response)
            spoke = bool(tts_results) and all(tts_results)
            if not spoke:
                logger.warning("tts_fallback_used: showing answer as text only")
        finally:
            self._hw.reset_exhibit()
            self._hw.set_status_led("off")

        logger.info(
            "[Timing] Cycle total %.0f ms [tts_ok=%s]",
            (time.perf_counter() - cycle_started) * 1000.0,
            spoke,
        )
        return SessionResult(
            detection=detection,
            transcript=transcript,
            dialogue=dialogue_result,
            tts_ok=bool(spoke),
        )
