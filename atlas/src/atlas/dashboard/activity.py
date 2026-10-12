"""Local, deterministic explanations of existing telemetry (no AI calls).

One entry contains both representations so a dashboard never fetches readable
text and its technical counterpart from different moments. Unknown messages
remain available in technical details; they are not invented into success.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Any

from atlas.config.settings import LoggingSettings
from atlas.models.languages import OUTPUT_LANGUAGE_NAMES

_PREFIX = re.compile(
    r"^(?P<time>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?"
    r"(?:Z|[+-]\d{2}:?\d{2})?)\s+(?P<level>DEBUG|INFO|WARNING|ERROR|CRITICAL)"
    r"\s+[^:]+:\s*"
)
_SPEECH = re.compile(
    r"\[(STT live|STT final|Typed question|LLM final|LLM sentence \d+|"
    r"ATLAS final|TTS message)\]"
)


def _speech_enabled(tag: str, settings: LoggingSettings) -> bool:
    if tag == "STT live":
        return settings.log_live_stt
    if tag in {"STT final", "Typed question"}:
        return settings.log_transcripts
    return settings.log_llm_responses


def safe_runtime_line(line: str, settings: LoggingSettings) -> str:
    """Also hide historical speech when the active privacy switch is off."""
    match = _SPEECH.search(line)
    if match and not _speech_enabled(match[1], settings):
        return line[: match.end()] + " [text hidden by active privacy settings]"
    return line


def safe_event(event: dict[str, Any], settings: LoggingSettings) -> dict[str, Any]:
    clean = dict(event)
    if not settings.log_transcripts:
        clean.pop("transcript", None)
    return clean


def _level(message: str, declared: str = "") -> str:
    if declared in {"ERROR", "CRITICAL"}:
        return "error"
    if declared == "WARNING":
        return "warning"
    # Metadata such as error=none / fallback=False is not a failure.
    if re.search(
        r"\b(?:failed|exception|error occurred|all .* paths failed)\b", message, re.I
    ):
        return "error"
    if re.search(
        r"(?:^|\]\s+)(?:ERROR|CRITICAL)\b|error:\s+\w|"
        r"Traceback \(most recent call last\)|\b\w+(?:Error|Exception)\b",
        message,
    ):
        return "error"
    if "tts_fallback_used" in message:
        return "warning"
    if re.search(r"\b(?:warning|unavailable)\b|\bstopped:", message, re.I):
        return "warning"
    if re.search(r"\btts_ok=False\b|\berror=(?!none\b|None\b)[\w]+", message):
        return "error"
    if "fallback=True" in message or "fallback_used=True" in message:
        return "warning"
    return "info"


def explain_runtime(line: str) -> dict[str, str]:
    prefix = _PREFIX.match(line)
    message = line[prefix.end() :].strip() if prefix else line.strip()
    level = _level(message, prefix["level"] if prefix else "")
    result = {
        "actor": "System",
        "kind": "system",
        "level": level,
        "timestamp": prefix["time"] if prefix else "",
        "text": "A system update was recorded. "
        "Open technical details for more information.",
    }

    def update(actor: str, kind: str, text: str) -> dict[str, str]:
        result.update(actor=actor, kind=kind, text=text)
        return result

    speech = _SPEECH.search(message)
    if speech:
        # A visitor saying "error" or "failed" is not a system fault.
        result["level"] = _level("", prefix["level"] if prefix else "")
        tag = speech[1]
        text = re.sub(r"\s+\[language=[^\]]+\]$", "", message[speech.end() :].strip())
        visitor = tag.startswith("STT") or tag == "Typed question"
        if "[text hidden by active privacy settings]" in text:
            description = (
                "The visitor is speaking."
                if tag == "STT live"
                else "The visitor's question was received."
                if visitor
                else "ATLAS prepared a response."
            )
            return update(
                "User" if visitor else "ATLAS",
                "conversation",
                description + " Quoted text is off in privacy settings.",
            )
        description = (
            "Speaking (not yet final): "
            if tag == "STT live"
            else "Question: "
            if visitor
            else "Response: "
            if tag in {"LLM final", "ATLAS final", "TTS message"}
            else "Response segment: "
        )
        return update(
            "User" if visitor else "ATLAS",
            "conversation",
            description + "“" + text + "”",
        )

    if "tts_fallback_used" in message or "tts_ok=False" in message:
        return update(
            "Voice",
            "voice",
            "The answer could not be played aloud. Text may be available, "
            "but speech needs attention.",
        )
    if level == "error":
        actor, kind = (
            ("Listening", "listening")
            if "[STT]" in message or "[Deepgram]" in message
            else ("Voice", "voice")
            if "[TTS]" in message or "[Cartesia]" in message
            else ("Camera", "camera")
            if "[Vision]" in message or "[Capture]" in message or "Camera" in message
            else ("ATLAS", "conversation")
            if "[Gemini]" in message or "[LLM]" in message
            else ("System", "system")
        )
        return update(
            actor,
            kind,
            f"{actor} reported a problem. "
            "Check the technical details; this entry does not confirm recovery.",
        )

    if "[Button] Manual artwork capture requested" in message:
        return update(
            "Button",
            "button",
            "The headset multifunction button was pressed. "
            "ATLAS will identify the artwork in front of the camera.",
        )
    if "[Capture] Identifying" in message:
        return update(
            "Camera", "camera", "ATLAS is checking the artwork centred in the camera."
        )
    if "[Capture] Context selected:" in message:
        title = message.split("Context selected:", 1)[1].split(";", 1)[0].strip()
        return update(
            "Camera",
            "camera",
            f"The camera identified {title}. ATLAS is now using this artwork "
            "as context and is still listening.",
        )
    if "[Capture] Stopped:" in message:
        return update(
            "Camera",
            "camera",
            "Artwork capture did not complete. Try pointing the camera at "
            "the artwork and pressing the button again.",
        )
    match = re.search(
        r"\[Vision\] (Triggered|Holding|Detected|Context) "
        r"(.+?)(?: after [\d.]+s| \(| \[|$)",
        message,
    )
    if match:
        action, title = match.groups()
        descriptions = {
            "Triggered": f"The camera detected {title}. This artwork is now selected.",
            "Holding": f"The camera sees {title} and is checking "
            "that the view is steady.",
            "Detected": f"The camera detected {title}.",
            "Context": f"ATLAS is using {title} for this question.",
        }
        return update(
            "Camera" if action != "Context" else "ATLAS", "camera", descriptions[action]
        )
    if "Gaze cleared" in message:
        return update(
            "Camera",
            "camera",
            "The previous artwork left the camera view. "
            "The camera is ready to recognise another artwork.",
        )
    if "Artwork context selected" in message:
        return update(
            "ATLAS",
            "camera",
            "The recognised artwork is now the conversation context. "
            "Listening continues.",
        )
    if "No active context" in message:
        return update(
            "Knowledge",
            "knowledge",
            "No artwork is selected. ATLAS is searching across "
            "the collection for the question.",
        )
    if "[STT] Preparing to listen" in message or "[Deepgram] Listening" in message:
        code = re.search(r"language=([\w-]+)", message)
        language = (
            OUTPUT_LANGUAGE_NAMES.get(code[1].split("-")[0], "the selected language")
            if code
            else "the selected language"
        )
        return update(
            "Listening",
            "listening",
            f"The microphone is listening in {language}. "
            "The visitor can ask a question.",
        )
    if "[Silero VAD] Speech started" in message:
        return update(
            "Listening",
            "listening",
            "Speech was detected. ATLAS is listening to the visitor's question.",
        )
    if "[STT] No transcript" in message:
        return update(
            "Listening",
            "listening",
            "No usable question was heard this time. Listening will continue "
            "when the next listening window opens.",
        )
    if "[STT] Final result" in message:
        return update(
            "User",
            "conversation",
            "The visitor's question was transcribed and is ready for ATLAS to answer.",
        )
    if "[STT] Provider used:" in message:
        return update(
            "Listening",
            "listening",
            "Speech recognition completed for this listening window.",
        )
    if "[RAG] Retrieved" in message:
        return update(
            "Knowledge",
            "knowledge",
            "ATLAS found museum information to help answer the question.",
        )
    if "[RAG]" in message and level == "info":
        return update(
            "Knowledge", "knowledge", "ATLAS is checking the museum knowledge base."
        )
    if "[Cartesia] First audio received" in message:
        return update(
            "Voice",
            "voice",
            "The first audio arrived from the voice service. Playback can begin.",
        )
    if "[Cartesia] Continuous synthesis complete" in message:
        return update(
            "Voice",
            "voice",
            "The voice service finished generating the response audio.",
        )
    if (
        "[TTS] Response voice locked" in message
        or "[Cartesia] Continuous context opened" in message
    ):
        return update(
            "Voice", "voice", "One voice was selected for the whole response."
        )
    if "[TTS] Continuous segment" in message:
        return update(
            "Voice",
            "voice",
            "Another audio segment was prepared using the same response voice.",
        )
    if "[Cartesia] Continuous synthesis started" in message:
        return update(
            "Voice", "voice", "ATLAS started generating speech for the response."
        )
    if "Response ready" in message:
        return update("ATLAS", "conversation", "ATLAS has prepared an answer.")
    if "[Timing] Scripted FAQ" in message:
        return update(
            "ATLAS", "conversation",
            "ATLAS used a verified museum answer for this question.",
        )
    if "[Timing] Cycle total" in message:
        return update(
            "ATLAS",
            "conversation",
            "This question-and-answer cycle finished"
            + ("; speech playback was confirmed." if "tts_ok=True" in message else "."),
        )
    if "[Timing]" in message:
        return update(
            "System", "system", "ATLAS recorded how long this processing step took."
        )
    if "[Cycle] Complete" in message:
        return update(
            "ATLAS", "conversation", "ATLAS finished responding to this question."
        )
    if "[Cycle] Stopped:" in message:
        return update(
            "ATLAS",
            "conversation",
            "The interaction ended before completion. "
            "Review the technical details for the reason.",
        )
    if "[Session] Active:" in message:
        return update("Session", "session", "A visitor session is active.")
    if "[Demo] Inviting artwork follow-up" in message:
        return update(
            "ATLAS", "conversation",
            "ATLAS is inviting the visitor to ask about the selected artwork.",
        )
    if "[Startup]" in message:
        return update(
            "System",
            "system",
            "ATLAS finished its startup checks. "
            "Component results follow in the technical output.",
        )
    actor, kind = next(
        (
            (label, kind)
            for marker, label, kind in (
                ("[STT]", "Listening", "listening"),
                ("[Deepgram]", "Listening", "listening"),
                ("[TTS]", "Voice", "voice"),
                ("[Cartesia]", "Voice", "voice"),
                ("[Gemini]", "ATLAS", "conversation"),
                ("[LLM]", "ATLAS", "conversation"),
                ("[Vision]", "Camera", "camera"),
                ("Camera", "Camera", "camera"),
            )
            if marker in message
        ),
        ("System", "system"),
    )
    if level != "info":
        return update(
            actor,
            kind,
            f"{actor} reported a problem. Check the technical details; "
            "this entry does not confirm recovery.",
        )
    if actor == "ATLAS":
        return update(actor, kind, "ATLAS is preparing an answer.")
    return update(
        actor,
        kind,
        f"{actor} recorded an update. Open technical details for more information.",
    )


_EVENTS = {
    "session_start": ("Session", "session", "A visitor session started."),
    "demo_session_start": ("Session", "session", "A demonstration session started."),
    "session_stop": ("Session", "session", "The visitor session ended."),
    "settings_updated": (
        "System",
        "system",
        "Dashboard settings were saved. A runtime restart is needed to apply them.",
    ),
    "START_LISTENING": (
        "Listening",
        "listening",
        "The microphone is ready for a question.",
    ),
    "AUDIO_CAPTURED": (
        "Listening",
        "listening",
        "Speech was captured for recognition.",
    ),
    "TRANSCRIBED": ("User", "conversation", "The visitor's question was transcribed."),
    "ARTWORK_DETECTED": ("Camera", "camera", "The camera recognised an artwork."),
    "RETRIEVED": ("Knowledge", "knowledge", "ATLAS found relevant museum information."),
    "GENERATED": ("ATLAS", "conversation", "ATLAS prepared an answer."),
    "VALIDATION_PASSED": (
        "Knowledge",
        "knowledge",
        "The answer passed its content checks.",
    ),
    "VALIDATION_FAILED_RETRY": (
        "Knowledge",
        "knowledge",
        "The answer needs another content check. ATLAS will retry.",
    ),
    "VALIDATION_FAILED_FALLBACK": (
        "Knowledge",
        "knowledge",
        "The answer did not pass its checks. ATLAS selected a safer fallback.",
    ),
    "SPOKEN": ("Voice", "voice", "The response was spoken."),
    "FOLLOWUP_RECEIVED": ("User", "conversation", "A follow-up question was received."),
    "FOLLOWUP_TIMEOUT": (
        "Listening",
        "listening",
        "No follow-up was received in this listening window.",
    ),
    "RESET": (
        "Session",
        "session",
        "The interaction was reset and is ready to start again.",
    ),
    "ERROR_OCCURRED": (
        "System",
        "system",
        "ATLAS reported an interaction error. Review the technical details.",
    ),
}


def explain_event(event: dict[str, Any], titles: dict[str, str]) -> dict[str, str]:
    name = str(event.get("event", ""))
    actor, kind, text = _EVENTS.get(
        name,
        (
            "System",
            "system",
            "A session update was recorded. "
            "Open technical details for more information.",
        ),
    )
    if name == "typed_question":
        actor, kind = "User", "conversation"
        text = (
            "Dashboard question: “" + str(event["transcript"]) + "”"
            if event.get("transcript")
            else "A question was submitted from the dashboard. "
            "Quoted text is off or was not recorded."
        )
    if name == "ARTWORK_DETECTED" and event.get("artwork_id"):
        title = titles.get(str(event["artwork_id"]), "an artwork")
        text = f"The camera recognised {title}."
    level = (
        "error"
        if event.get("error_type") or name == "ERROR_OCCURRED"
        else "warning"
        if event.get("fallback_used") or name.startswith("VALIDATION_FAILED")
        else "info"
    )
    if level == "error":
        text = f"{actor} reported an interaction error. " + (
            "Review the technical details; completion is not confirmed."
        )
    elif event.get("fallback_used"):
        text += " A backup or safer response path was used."
    return {
        "actor": actor,
        "kind": kind,
        "text": text,
        "level": level,
        "timestamp": str(event.get("timestamp") or ""),
    }


def pair_entries(raw: list[Any], source: str, explain) -> list[dict[str, Any]]:
    """IDs distinguish repeated messages without inventing event timestamps."""
    occurrences: Counter[str] = Counter()
    entries = []
    for item in raw:
        digest = hashlib.sha256(
            json.dumps(item, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:20]
        occurrences[digest] += 1
        entries.append(
            {
                "id": f"{source}-{digest}-{occurrences[digest]}",
                "source": source,
                "raw": item,
                **explain(item),
            }
        )
    return entries
