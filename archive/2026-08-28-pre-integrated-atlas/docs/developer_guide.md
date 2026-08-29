# ATLAS developer guide

## Setup (Windows PowerShell shown; macOS/Linux equivalent in parentheses)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # (source .venv/bin/activate)
pip install -e ".[dev]"               # core + pytest + ruff + httpx
copy .env.example .env                # (cp .env.example .env)
```

Optional heavy extras (never needed for dev mode):

```powershell
pip install -e ".[rag]"      # ChromaDB + sentence-transformers + BM25
pip install -e ".[vision]"   # ultralytics (YOLO)
pip install -e ".[audio]"    # faster-whisper + piper
pip install -e ".[llm]"      # google-generativeai (Gemini)
```

## Daily commands

```powershell
python -m pytest -q                                # test suite
python -m atlas.app.main --run 3                   # 3 full mock cycles
python -m atlas.rag.ingest --pack data/content_packs/demo_pack --mode dev --reset
python -m atlas.rag.evaluator                      # RAG guardrail eval
python -m uvicorn atlas.dashboard.api:app --host 127.0.0.1 --port 8765
ruff check src tests
```

## Code map

```
src/atlas/
  app/         main, state_machine, events, dependency_container (DI root)
  config/      settings (pydantic, extra=forbid), loader (yaml + env)
  models/      artwork, content_pack, dialogue, retrieval, session,
               telemetry, enums
  rag/         ingest, chunking, embeddings, chroma_store, sqlite_fts_store,
               fusion (RRF), reranker, retriever, context_packer, evaluator
  dialogue/    dialogue_engine, prompt_builder, gemini_client,
               mock_llm_client, grounding_validator, safety_filter
  safety/      prompt_injection_filter
  vision/      detector (base), mock_detector, yolo_detector, tracker
  audio/       stt/tts bases, mocks, whisper_stt, piper_tts
  hardware/    base (emergency stop lives here), mock_hardware, ev3_hardware
  pipeline/    session_runner
  dashboard/   api, schemas, runtime_service, auth, templates/, static/
  storage/     event_logger (privacy blocklist), sqlite_db
  utils/       ids, text, time
```

## Conventions

- Inspect real signatures before patching; components hide behind base
  classes (`BaseDetector`, `BaseSTT`, `BaseTTS`, `BaseHardware`).
- Dependency injection through the container only; no global singletons.
- Settings models use `extra="forbid"`: add the field to
  `src/atlas/config/settings.py` **before** adding it to
  `config/settings.yaml`.
- Privacy: never log raw audio/images, names, keys, or prompts. The
  `EventLogger` blocklist is the last line of defence, not the first.
- Secrets only via environment variables (`.env`, never committed).
- Keep mock/dev mode green after every change:
  `python -m pytest -q && python -m atlas.app.main --run 3`.
- No hard-coded OS-specific paths; use `pathlib`.

## Adding a real adapter

1. Implement the base interface in the matching package.
2. Wire it in `dependency_container.py` behind a `RunMode`/settings check.
3. Fail gracefully (log + return None/False) — never crash the cycle.
4. Add a mock-backed test; hardware itself is never required by tests.

## Testing notes

- Dashboard tests build an isolated container on `tmp_path` and ingest the
  demo pack into it — they never touch `data/`.
- `fastapi.testclient` needs `httpx` (in the dev extra).
- Do not delete or weaken existing tests to make a change pass.
