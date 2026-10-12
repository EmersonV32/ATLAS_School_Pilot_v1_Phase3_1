"""Readable activity uses synthetic telemetry, never installation logs."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from atlas.config.settings import LoggingSettings, PathsSettings, Settings
from atlas.dashboard.activity import (
    explain_event,
    explain_runtime,
    pair_entries,
    safe_event,
    safe_runtime_line,
)
from atlas.dashboard.runtime_service import RuntimeService
from atlas.storage.event_logger import EventLogger


@pytest.mark.parametrize(
    "line,actor,text",
    [
        (
            "[STT] Preparing to listen [language=fr timeout=45.0s]",
            "Listening",
            "French",
        ),
        ("[Deepgram] Listening with Silero VAD", "Listening", "microphone"),
        ("[Silero VAD] Speech started", "Listening", "Speech was detected"),
        ("[STT live] who is in [language=en final=False]", "User", "not yet final"),
        ("[STT final] Who is in the Mona Lisa?", "User", "“Who is in the Mona Lisa?”"),
        ("[STT] Final result [language=en confidence=0.94]", "User", "transcribed"),
        ("[STT] No transcript returned", "Listening", "No usable question"),
        ("[STT] Provider used: Deepgram", "Listening", "completed"),
        (
            "[LLM sentence 1] The Mona Lisa depicts Lisa Gherardini.",
            "ATLAS",
            "Response segment",
        ),
        (
            "[LLM final] The Mona Lisa is a portrait.",
            "ATLAS",
            "“The Mona Lisa is a portrait.”",
        ),
        (
            "[Button] Manual artwork capture requested [clicks=2 action=capture]",
            "Button",
            "multifunction button was pressed",
        ),
        (
            "[Capture] Identifying the centered artwork...",
            "Camera",
            "checking the artwork",
        ),
        (
            "[Capture] Context selected: Mona Lisa; listening remains active",
            "Camera",
            "identified Mona Lisa",
        ),
        ("[Capture] Stopped: no_detection", "Camera", "did not complete"),
        (
            "[Vision] Holding Mona Lisa (94%, center=0.88)",
            "Camera",
            "checking that the view is steady",
        ),
        (
            "[Vision] Triggered Mona Lisa after 1.2s",
            "Camera",
            "Mona Lisa. This artwork is now selected",
        ),
        (
            "[Vision] Detected The Starry Night "
            "[artwork_id=starry_night confidence=96%]",
            "Camera",
            "The Starry Night",
        ),
        (
            "[Vision] Context Mona Lisa [artwork_id=mona_lisa confidence=94%]",
            "ATLAS",
            "using Mona Lisa for this question",
        ),
        (
            "[Vision] Gaze cleared; ready for another artwork",
            "Camera",
            "previous artwork left",
        ),
        (
            "[Vision] Artwork context selected; continuous listening unchanged",
            "ATLAS",
            "Listening continues",
        ),
        (
            "[Vision] No active context; searching all artworks",
            "Knowledge",
            "searching across",
        ),
        ("[RAG] Retrieved 4 chunks [latency_ms=12]", "Knowledge", "museum information"),
        ("[TTS] Response voice locked voice=x", "Voice", "One voice"),
        ("[Cartesia] Continuous context opened", "Voice", "One voice"),
        ("[Cartesia] First audio received", "Voice", "first audio arrived"),
        (
            "[Cartesia] Continuous synthesis complete",
            "Voice",
            "generating the response audio",
        ),
        ("[TTS] Continuous segment 2", "Voice", "same response voice"),
        (
            "tts_fallback_used: showing answer as text only",
            "Voice",
            "could not be played aloud",
        ),
        ("[Timing] Cycle total 900ms [tts_ok=True]", "ATLAS", "playback was confirmed"),
        (
            "[Timing] Cycle total 900ms [tts_ok=False]",
            "Voice",
            "speech needs attention",
        ),
        ("[Gemini] Request started", "ATLAS", "preparing an answer"),
        ("[Session] Active: synthetic-session", "Session", "session is active"),
        ("A new unrecognised subsystem marker", "System", "Open technical details"),
    ],
)
def test_runtime_updates_are_readable_without_debug_metadata(line, actor, text):
    update = explain_runtime(line)
    assert update["actor"] == actor
    assert text in update["text"]
    assert "artwork_id=" not in update["text"]
    assert "confidence=" not in update["text"]
    assert update["timestamp"] == ""


def test_timestamp_and_fault_are_not_relabelled_as_healthy():
    update = explain_runtime(
        "2026-10-12 10:23:45 ERROR atlas.pipeline: [STT] All paths failed"
    )
    assert update["timestamp"] == "2026-10-12 10:23:45"
    assert update["level"] == "error"
    assert "reported a problem" in update["text"]
    assert "does not confirm recovery" in update["text"]


@pytest.mark.parametrize(
    "line",
    [
        "[Timing] LLM [fallback=False error=none]",
        "[STT final] Why did the artist's experiment fail with an error?",
        "[LLM final] This error was part of the artist's experiment.",
    ],
)
def test_words_inside_speech_and_non_failure_metadata_are_not_faults(line):
    assert explain_runtime(line)["level"] == "info"


@pytest.mark.parametrize(
    "tag,switch",
    [
        ("STT final", "log_transcripts"),
        ("Typed question", "log_transcripts"),
        ("STT live", "log_live_stt"),
        ("LLM final", "log_llm_responses"),
        ("LLM sentence 1", "log_llm_responses"),
        ("ATLAS final", "log_llm_responses"),
        ("TTS message", "log_llm_responses"),
    ],
)
def test_quotes_follow_each_active_privacy_switch_in_both_representations(tag, switch):
    original = f"[{tag}] quoted synthetic speech"
    hidden = safe_runtime_line(original, LoggingSettings())
    assert "quoted synthetic speech" not in hidden
    assert "quoted synthetic speech" not in explain_runtime(hidden)["text"]
    enabled = LoggingSettings(**{switch: True})
    assert safe_runtime_line(original, enabled) == original
    assert "quoted synthetic speech" in explain_runtime(original)["text"]


def test_existing_typed_question_and_local_answer_tags_use_readable_speakers():
    question = explain_runtime("[Typed question] Who painted the Mona Lisa?")
    answer = explain_runtime("[ATLAS final] Leonardo da Vinci painted the Mona Lisa.")
    assert question["actor"] == "User"
    assert "“Who painted the Mona Lisa?”" in question["text"]
    assert answer["actor"] == "ATLAS"
    assert "Response: “Leonardo da Vinci" in answer["text"]


def test_event_translation_and_privacy_do_not_mutate_source():
    event = {"event": "typed_question", "transcript": "Who painted this?"}
    hidden = safe_event(event, LoggingSettings())
    assert "transcript" not in hidden
    assert "Who painted this?" in event["transcript"]
    assert "off or was not recorded" in explain_event(hidden, {})["text"]
    assert "Who painted this?" in explain_event(event, {})["text"]
    assert (
        explain_event(
            {"event": "ARTWORK_DETECTED", "artwork_id": "mona_lisa"},
            {"mona_lisa": "Mona Lisa"},
        )["text"]
        == "The camera recognised Mona Lisa."
    )


@pytest.mark.parametrize(
    "name",
    [
        "START_LISTENING",
        "AUDIO_CAPTURED",
        "TRANSCRIBED",
        "ARTWORK_DETECTED",
        "RETRIEVED",
        "GENERATED",
        "VALIDATION_PASSED",
        "SPOKEN",
        "FOLLOWUP_RECEIVED",
        "FOLLOWUP_TIMEOUT",
        "RESET",
        "session_start",
        "demo_session_start",
        "session_stop",
        "settings_updated",
    ],
)
def test_structured_lifecycle_has_specific_plain_language(name):
    assert "A session update" not in explain_event({"event": name}, {})["text"]


@pytest.mark.parametrize(
    "event,level",
    [
        ({"event": "ERROR_OCCURRED"}, "error"),
        ({"event": "GENERATED", "error_type": "timeout"}, "error"),
        ({"event": "VALIDATION_FAILED_RETRY"}, "warning"),
        ({"event": "GENERATED", "fallback_used": True}, "warning"),
    ],
)
def test_structured_errors_and_fallbacks_have_correct_severity(event, level):
    assert explain_event(event, {})["level"] == level
    if level == "error":
        assert "completion is not confirmed" in explain_event(event, {})["text"]


@pytest.mark.parametrize(
    "line",
    [
        "[Timing] Cycle total 1000ms [tts_ok=True error=timeout]",
        "[Gemini] Request failed: TimeoutError",
        "ERROR Camera could not open",
        "Camera error: RuntimeError",
        "Traceback (most recent call last):",
    ],
)
def test_failure_metadata_never_becomes_a_success_story(line):
    update = explain_runtime(line)
    assert update["level"] == "error"
    assert "reported a problem" in update["text"]


def test_duplicate_rows_are_preserved_and_paired_deterministically():
    lines = ["[STT] No transcript returned"] * 2
    entries = pair_entries(lines, "runtime", explain_runtime)
    assert len(entries) == 2
    assert entries[0]["id"] != entries[1]["id"]
    assert [entry["raw"] for entry in entries] == lines
    assert entries == pair_entries(lines, "runtime", explain_runtime)


def test_snapshot_reads_each_source_once_and_pairs_same_content(tmp_path, monkeypatch):
    settings = Settings(paths=PathsSettings(logs_dir=tmp_path))
    service = RuntimeService(SimpleNamespace(settings=settings))
    calls = []

    def runtime(limit):
        calls.append(("runtime", limit))
        return {"available": True, "lines": ["[STT final] hidden old speech"]}

    def events(limit):
        calls.append(("events", limit))
        return [{"event": "typed_question", "transcript": "hidden old question"}]

    monkeypatch.setattr(service, "runtime_logs", runtime)
    monkeypatch.setattr(service, "recent_logs", events)
    monkeypatch.setattr(service, "_artwork_map", lambda: {})
    snapshot = service.log_snapshot(limit=9999, event_limit=-1)
    assert calls == [("runtime", 1000), ("events", 1)]
    assert "hidden old" not in json.dumps(snapshot)
    assert len(snapshot["runtime"]) == len(snapshot["events"]) == 1
    assert snapshot["runtime"][0]["source"] == "runtime"
    assert snapshot["events"][0]["source"] == "events"
    assert snapshot["snapshot_id"] == service.log_snapshot()["snapshot_id"]


def test_event_tail_is_bounded_unicode_safe_and_skips_incomplete_rows(tmp_path):
    event_logger = EventLogger(tmp_path, LoggingSettings())
    path = event_logger._log_path()
    path.write_text(
        ('{"event":"old","extra":"' + "x" * 80000 + '"}\n')
        + '{"event":"ready","artwork_id":"La Joconde — musée"}\n'
        + '{"event":"unfinished"',
        encoding="utf-8",
    )
    assert event_logger.read_recent(limit=2) == [
        {"event": "ready", "artwork_id": "La Joconde — musée"},
    ]


def test_event_tail_ignores_valid_json_that_is_not_an_event_object(tmp_path):
    event_logger = EventLogger(tmp_path, LoggingSettings())
    event_logger._log_path().write_text(
        '[]\n7\n"not an event"\n{"event":"ready"}\n',
        encoding="utf-8",
    )
    assert event_logger.read_recent() == [{"event": "ready"}]


@pytest.mark.parametrize(
    "line,level",
    [
        ("tts_fallback_used: showing answer as text only", "warning"),
        ("[Timing] LLM [fallback=True error=none]", "warning"),
        ("[Timing] LLM [fallback_used=False error=none]", "info"),
        ("[Capture] Stopped: no_detection", "warning"),
    ],
)
def test_fallbacks_and_early_stops_are_not_mistaken_for_healthy_updates(line, level):
    assert explain_runtime(line)["level"] == level
