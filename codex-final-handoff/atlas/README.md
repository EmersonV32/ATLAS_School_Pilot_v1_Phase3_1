# ATLAS School Pilot v1.0

Wearable AI museum guide and cultural mediation system, by Team Touchdown
(Collège Bourget, WRO 2026 Future Innovators). ATLAS turns museum displays
into dialogue: it identifies what a visitor is looking at, answers questions
in the visitor's language and level, and creates a personalized, accessible
cultural experience.

*Atlas — because every story deserves a listener.*

> ATLAS uses an edge-first architecture: vision, speech, retrieval, motor
> control, and text-to-speech run locally or nearby, while the current
> prototype uses a cloud language model for final response generation. A
> future version aims to replace this with an on-device language model.

ATLAS is **not** fully offline and does not claim to be. Cloud LLM mode is
documented, opt-in, and disclosed (see `docs/cloud_llm_disclosure.md`).

## Complete recovery bundle

The repository now includes the integrated runtime, XIAO firmware, EV3 code,
the authoritative YOLO checkpoint, exact Jetson package snapshot, setup and
repair history, prior reports, and an exact archived snapshot of the nationals
repository. Start with `docs/recovery/REBUILD_FROM_FRESH_FLASH.md` after a
reflash. Credentials and device-generated TensorRT/cache files are the only
intentional exclusions.

## Status: School Pilot v1.0

The full pipeline runs in dev mode with no hardware, no API key and no ML
downloads, and real adapters (YOLO, Whisper, Piper, Gemini, EV3) are wired
behind the same interfaces for device/demo modes.

| Area | Status |
|------|--------|
| State machine, config, privacy-safe logging | Done |
| Hybrid RAG (Chroma/simple dense + SQLite FTS5/BM25 + RRF k=60 + reranker + level fallback) | Done |
| Dialogue (prompt builder, JSON contract, grounding validation, refusal fallbacks EN/FR) | Done |
| Safety (prompt-injection filter, content filter, privacy defaults) | Done |
| Vision (mock + YOLO adapter + ArtworkTracker with manual override) | Done |
| Audio (mock + Whisper STT / Piper TTS adapters, graceful failure) | Done |
| Hardware (mock + EV3 adapter, emergency stop) | Done |
| Teacher dashboard (local FastAPI + vanilla JS) | Done |
| Codex admin copilot (allowlisted tools + approvals, opt-in) | Done |
| Tests (pytest, incl. dashboard + privacy) | Done |
| School-pilot docs (`docs/`) | Done |

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
pip install -e ".[admin-ai]"         # OpenAI SDK for protected admin Codex
```

## Run

```bash
# Ingest the demo content pack (writes to data/sqlite + data/chroma)
python -m atlas.rag.ingest --pack data/content_packs/demo_pack --mode dev --reset

# Run full mock pipeline cycles (no hardware, no API key, no ML downloads)
python -m atlas.app.main --run 3

# Scripted state-machine walkthrough
python -m atlas.app.main --mode dev

# Teacher dashboard (localhost only) — open http://127.0.0.1:8765
python -m uvicorn atlas.dashboard.api:app --host 127.0.0.1 --port 8765

# RAG evaluation guardrail (factual/visual/interpretive/French/refusal/
# injection/accessibility categories)
python -m atlas.rag.evaluator

# Tests
pytest

# Lint
ruff check src tests
```

Admin-protected dashboard actions (content ingest, RAG eval, demo
simulations, clearing the emergency stop) require the `ATLAS_ADMIN_TOKEN`
environment variable and the matching `X-Atlas-Admin-Token` header (the
dashboard UI has a token field).

The optional Ask Codex admin panel also requires
`ATLAS_ADMIN_AI_ENABLED=true`, a server-side `OPENAI_API_KEY`, and the
`admin-ai` extra. Mutations require a second authenticated approval and Codex
has no shell, SSH, or deployment tool. See
`docs/admin_ai/CODEX_ADMIN_COPILOT.md`.

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
  CLAUDE.md               Claude Code project instructions
  .claude/commands/       atlas-status, atlas-test, atlas-run, atlas-dashboard,
                          atlas-rag-ingest, atlas-rag-eval, atlas-device-check
  config/                 settings.yaml, profiles.yaml, hardware.yaml
  data/                   content_packs/, chroma/, sqlite/, logs/
  docs/                   architecture, developer/teacher guides, privacy
                          summary, cloud LLM disclosure, troubleshooting,
                          content pack format, device demo checklist,
                          school pilot runbook, demo script
  src/atlas/
    app/                  state_machine, events, dependency_container, main
    config/               settings (pydantic), loader (yaml + env)
    models/               artwork, content_pack, dialogue, retrieval, session,
                          telemetry, enums
    storage/              event_logger (privacy-safe JSON logs)
    utils/                ids, time, text
    rag/                  ingest, stores, RRF fusion, reranker, retriever,
                          context packer, evaluator
    dialogue/             engine, prompt builder, Gemini/mock clients,
                          grounding validator, safety filter
    safety/               prompt_injection_filter
    vision/               detector base, mock, YOLO adapter, ArtworkTracker
    audio/                STT/TTS bases, mocks, Whisper/Piper adapters
    hardware/             base (emergency stop), mock, EV3 adapter
    pipeline/             session_runner
    dashboard/            FastAPI api, runtime service, auth, HTML/JS UI
  tests/                  full suite incl. dashboard API + privacy tests
```

## Documentation

Start with `docs/architecture.md` (system design),
`docs/developer_guide.md` (contributing), `docs/teacher_guide.md` (running a
class session), and `docs/privacy_summary.md` (what is and is not stored).

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

## Dialogue safety (v1.0)

Questions pass a prompt-injection filter before any LLM call; retrieved
content is treated as data, not instructions. Real-LLM answers use a JSON
contract (`spoken_answer`, `used_chunk_ids`, `confidence`,
`unsupported_claims`, `fallback_used`); cited chunk IDs are validated
against what was actually retrieved, and ungrounded answers are replaced
with a spoken refusal ("I don't have that detail verified in my guide
yet…") in the visitor's language. A content safety filter runs last, before
TTS.

## Hardware notes (device mode)

- Vision: train YOLO weights on the approved artworks and set
  `hardware.yolo_model_path`; the ArtworkTracker stabilises detections and
  supports dashboard manual override.
- Audio: faster-whisper STT and Piper TTS on Jetson with the Shokz
  OpenComm2 UC headset (`hardware.whisper_model_size`, `piper_voice_*`).
- EV3 stand: set `hardware.ev3_bt_address` + `enable_ev3: true`. Emergency
  stop (dashboard) blocks all movement until cleared with the admin token.
- The KY-016 RGB LED GPIO is broken on JetPack 6.x (pins 29/31/33) — the
  EV3 status LED is used instead and the KY-016 is not critical path.
- FeeTech FT5478M servo expects ~7.4 V; verify the PSU before enabling.
- Board target: Jetson Orin Nano now; Seeed reComputer Super J401
  Orin NX 16 GB planned (JetPack 6.x).

See `docs/device_demo_checklist.md` for the staged validation ladder (A–F)
and `docs/school_pilot_v1_runbook.md` for running an actual pilot session.
