# ATLAS privacy summary (school pilot v1.0)

ATLAS is privacy-conscious museum technology designed for use with students.
These defaults are enforced in code and configuration, and verified by
automated tests (`tests/test_dashboard_privacy.py`).

## What ATLAS does NOT store (by default, and in the pilot)

| Data | Stored? | Enforcement |
|------|---------|-------------|
| Raw audio recordings | **No** | `privacy.store_raw_audio: false`; audio never reaches the logging layer |
| Raw images / video | **No** | `privacy.store_raw_images: false`; frames are processed in memory only |
| Face data / facial recognition | **No — feature does not exist** | `privacy.store_face_data: false`; no face models in the codebase |
| Student names | **No — never collected** | `privacy.student_names_required: false`; no name field anywhere |
| Question transcripts | **Not by default** | `logging.log_transcripts: false`; when a school explicitly enables it, transcripts are sanitized and truncated |
| API keys / secrets | **Never** | Keys live only in environment variables; the log blocklist drops key-like fields |
| Gender inference | **No — feature does not exist** | — |

## What ATLAS logs (privacy-safe telemetry)

One JSON line per event with: timestamp, **anonymous** session ID, state,
event name, language, artwork ID, vision confidence, component latencies
(STT/retrieval/LLM/TTS), fallback flag, and error codes. Nothing else.

The logger (`src/atlas/storage/event_logger.py`) has a hard blocklist that
drops audio/image/name/key/prompt fields even if passed by mistake.

## Retention

Log retention target is configurable (`logging.retention_days`, default 30).
Log files are plain JSON lines under `data/logs/` and can be deleted at any
time by the school.

## Cloud disclosure

ATLAS is edge-first, **not** fully offline. When (and only when) the cloud
LLM is enabled (`llm.cloud_llm_enabled: true`), the question text and
retrieved artwork notes are sent to Google Gemini to compose the final
answer. See `CLOUD_LLM_DISCLOSURE.md`. In dev/mock mode no data leaves the
machine.

## Session model

- Session IDs are random and anonymous; they cannot be linked to a student.
- Session memory is not persistent (`privacy.session_memory_persistent: false`).
- The teacher dashboard runs on localhost only and is never exposed to the
  internet; dangerous actions require a local admin token.
