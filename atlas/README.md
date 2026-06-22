# ATLAS School Pilot v1

Wearable AI museum guide and cultural mediation system, by Team Touchdown
(WRO 2026 Future Innovators). ATLAS turns museum displays into dialogue: it
identifies what a visitor is looking at, answers questions in the visitor's
language and level, and creates a personalized, accessible cultural
experience.

> ATLAS uses an edge-first architecture: vision, speech, retrieval, motor
> control, and text-to-speech run locally or nearby, while the current
> prototype uses a cloud language model for final response generation. A
> future version aims to replace this with an on-device language model.

ATLAS is **not** fully offline and does not claim to be. Cloud LLM mode is
documented and configurable.

## Status: Phase 2 complete

This repository is being generated in phases. Phases 1-2 are done and the
full hybrid retrieval pipeline runs in dev mode with no hardware and no ML
downloads (stdlib + Pydantic only).

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Repo structure, schemas, config, state machine, logging | Done |
| 2 | RAG ingestion, dense + keyword retrieval, RRF, reranking, demo pack | Done |
| 3 | Dialogue engine, prompt builder, Gemini client + mock fallback, grounding validator, safety filters | Done |
| 4 | Vision (YOLO + mock), audio STT/TTS, hardware adapters, dashboard API | Next |
| 5 | Full test suite, content-pack expansion, setup docs, runbook | Planned |

## Requirements

- Python 3.10+
- Dev mode needs only the core dependencies (no GPU, no model downloads).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev]"              # core + pytest + ruff

cp .env.example .env                 # fill in GEMINI_API_KEY only if using gemini
```

Heavy components are opt-in so a laptop stays usable:

```bash
pip install -e ".[rag]"              # ChromaDB + sentence-transformers + BM25
pip install -e ".[vision]"           # ultralytics (YOLO)
pip install -e ".[audio]"            # faster-whisper + Piper
pip install -e ".[llm]"              # google-generativeai (Gemini)
```

## Run

```bash
# Phase 1 dev walkthrough (no hardware, no ML): drives the state machine
python -m atlas.app.main --mode dev

# Phase 2: ingest the demo content pack (writes to data/sqlite + data/chroma)
python -m atlas.rag.ingest --pack data/content_packs/demo_pack --mode dev

# Tests
pytest

# Lint
ruff check src tests
```

After ingesting, the hybrid retriever is available through the dependency
container (`Container.retriever`). A typed-question CLI and the teacher
dashboard that call it arrive in Phases 3-4. To try retrieval directly:

```python
from atlas.app.dependency_container import build_container
from atlas.models.enums import EducationalLevel, Intent, Language
from atlas.models.retrieval import RetrievalQuery

c = build_container()
result = c.retriever.retrieve(RetrievalQuery(
    text="why is the sky swirling",
    artwork_id="starry_night",
    language=Language.EN,
    educational_level=EducationalLevel.ADULT_BEGINNER,
    intent=Intent.VISUAL,
    top_k=3,
))
for chunk in result.chunks:
    print(chunk.rank, chunk.chunk_id, round(chunk.score, 3), chunk.text[:60])
```

Run modes (config `mode:` or `--mode`):

- `dev` — everything mocked, no hardware, no ML downloads
- `local` — real RAG, mock vision/audio (Phase 2+)
- `device` — real vision/STT/TTS on Jetson (Phase 4)
- `demo` — fixed artwork + typed questions (Phase 4)

## Configuration

- `config/settings.yaml` — app settings (paths, RAG params, LLM provider, logging)
- `config/profiles.yaml` — visitor profiles (child, teen, expert, visual_impairment, ...)
- `config/hardware.yaml` — camera/audio/Jetson/exhibit settings (device layer)
- `.env` — secrets only. **API keys live here, never in code or YAML.**

Settings precedence: model defaults < `settings.yaml` < environment overrides
(`ATLAS_MODE`, `ATLAS_DEFAULT_PACK`, `ATLAS_LLM_PROVIDER`, `ATLAS_LOG_TRANSCRIPTS`).

## Privacy and school safety (built in from Phase 1)

- No raw audio stored. No raw images/video stored. No facial recognition.
- No gender inference. No student names. Anonymous session IDs only.
- Structured JSON logs with a blocklist that drops sensitive keys even if
  passed by mistake (`storage/event_logger.py`).
- Transcript logging is **off by default** and configurable.
- API keys are read from the environment at call time, never logged.

## Repository layout

```
atlas/
  config/                 settings.yaml, profiles.yaml, hardware.yaml
  data/                   content_packs/, chroma/, sqlite/, logs/
  src/atlas/
    app/                  state_machine, events, dependency_container, main
    config/               settings (pydantic), loader (yaml + env)
    models/               artwork, content_pack, dialogue, retrieval, session,
                          telemetry, enums
    storage/              event_logger (privacy-safe JSON logs)
    utils/                ids, time, text
    vision/ audio/ rag/   (interfaces + mocks land in later phases)
    dialogue/ safety/
    dashboard/ hardware/
  tests/                  test_content_schema, test_state_machine (Phase 1)
```

## How retrieval works (Phase 2)

A question is answered by combining two searches and fusing them:

1. **Normalize** the query lightly (`rag/retriever.py`). Meaning is never
   changed; the raw transcript is kept separately for logs. A vague,
   pronoun-led question gets the detected artwork's title appended as an
   anchor.
2. **Dense** search (`rag/chroma_store.py`): embed the query and rank chunks
   by cosine similarity. Dev uses a dependency-free token-hashing embedder
   (`MockEmbedder`); `pip install -e ".[rag]"` swaps in sentence-transformers
   + ChromaDB behind the same interface.
3. **Keyword** search (`rag/sqlite_fts_store.py`): SQLite FTS5 with the
   built-in `bm25()` ranking, joined to the `chunks` table for metadata
   filtering. Falls back to a pure-Python BM25 if a SQLite build lacks FTS5.
4. Both searches filter on the same metadata: `artwork_id`, `language`,
   `educational_level`, `allowed_for_students = true`, `verified = true`.
5. **Reciprocal Rank Fusion** (`rag/fusion.py`): `score = sum 1/(k+rank)`,
   `k = 60`. Robust because it uses ranks, not raw scores.
6. **Rerank** (`rag/reranker.py`): a transparent heuristic boosts the
   matching artwork, the requested language, and the chunk type that fits the
   question's intent. A cross-encoder reranker is wired as an opt-in
   extension point.
7. **Pack** (`rag/context_packer.py`): the top chunks become a bounded,
   tagged context block (`[chunk_id=... source_id=...] text`) so the Phase 3
   grounding validator can verify the answer cites real retrieved chunks.

## Phase 3 roadmap (next)

1. `dialogue/intent_classifier.py`, `dialogue/query_rewriter.py`
2. `dialogue/prompt_builder.py` (profile- and language-aware system prompt)
3. `dialogue/llm_base.py`, `dialogue/gemini_client.py`, `dialogue/mock_llm.py`
   (structured JSON: spoken_answer, used_chunk_ids, confidence,
   unsupported_claims, fallback_used)
4. `dialogue/response_validator.py` (grounding + length + language + no
   secret leakage; regenerate once, else safe fallback)
5. `safety/prompt_injection_filter.py`, `safety/output_safety.py`,
   `safety/privacy_filter.py`
6. `dialogue/answer_service.py` tying retrieval -> prompt -> LLM -> validate
7. Tests: prompt builder, grounding validator, injection filter, answer
   service, unknown-question refusal

## Hardware-specific work to finish later (Phase 4)

- `vision/yolo_detector.py` against a YOLO model trained on the approved
  artworks (mock detector lets the pipeline run today).
- `audio/whisper_stt.py` (faster-whisper) and `audio/piper_tts.py` on Jetson
  with the Shokz OpenComm2 UC headset.
- `hardware/ev3_adapter.py` / `servo_controller.py` — note the FeeTech
  FT5478M expects ~7.4V; verify the PSU before enabling servo control.
- Board target: Seeed reComputer Super J401 NX 16GB, JetPack 6.1.
