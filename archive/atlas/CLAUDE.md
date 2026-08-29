# ATLAS — Claude Code project instructions

## Identity

ATLAS is a **wearable AI museum guide and cultural mediation system** by Team
Touchdown (Collège Bourget, WRO 2026 Future Innovators).

Slogan: **"Atlas — because every story deserves a listener."**

One-sentence pitch: ATLAS is a wearable AI museum guide that identifies what a
visitor is looking at, answers questions in the visitor's language and level,
and creates a personalized, accessible cultural experience. ATLAS turns museum
displays into dialogue.

Describe ATLAS as: wearable AI, contextual cultural intelligence, adaptive
cultural mediation, edge-first AI, accessibility-focused interaction,
privacy-conscious museum technology, a teacher-controlled educational AI
platform. Never describe it as "just a chatbot / robot / phone app / audio
guide / AI helmet."

## Technical truth (use this exact wording in docs)

> ATLAS uses an edge-first architecture: vision, speech, retrieval, motor
> control, and text-to-speech run locally or nearby, while the current
> prototype uses a cloud language model for final response generation. A
> future version aims to replace this with an on-device language model.

Never claim: fully offline, fully local, "no data is uploaded anywhere", or
"hallucinations are impossible."

## Stack

- Python 3.10+, `src/` layout, package `atlas` (installed as
  `atlas-museum-guide`), Pydantic v2 models, FastAPI + uvicorn (dashboard).
- RAG: ChromaDB dense (mock hash-embedder in dev) + SQLite FTS5/BM25 keyword
  → Reciprocal Rank Fusion (k=60) → heuristic reranker → context packer.
- Dialogue: PromptBuilder → LLM (MockLLMClient in dev, GeminiClient in
  device/demo) → GroundingValidator → SafetyFilter/injection filter.
- Vision: MockDetector / YoloDetector behind `BaseDetector`, plus
  ArtworkTracker (stability + manual override).
- Audio: MockSTT / WhisperSTT behind `BaseSTT`; MockTTS / PiperTTS behind
  `BaseTTS`.
- Hardware: MockHardware / EV3Hardware behind `BaseHardware`; optional, never
  required for dev.
- Everything is wired through `src/atlas/app/dependency_container.py`
  (lazy properties keyed on `RunMode`).

## Run modes

- `dev` — everything mocked; no hardware, no ML downloads. **Must always work.**
- `local` — real RAG, mock vision/audio.
- `device` — real vision/STT/TTS on Jetson.
- `demo` — fixed artwork + typed questions.

## Safe commands (Windows PowerShell, venv at .venv)

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q                                            # tests
python -m atlas.app.main --run 3                               # 3 mock cycles
python -m atlas.rag.ingest --pack data/content_packs/demo_pack --mode dev --reset
python -m uvicorn atlas.dashboard.api:app --host 127.0.0.1 --port 8765
ruff check src tests
```

## Privacy rules (non-negotiable defaults)

- No raw audio stored. No raw images/video stored. No facial recognition.
- No student names. Anonymous session IDs only.
- Transcript logging OFF by default; sanitized when enabled.
- API keys only via environment (`.env`, `GEMINI_API_KEY`), read at call
  time, never logged, never committed.
- `storage/event_logger.py` has a blocklist that drops sensitive keys —
  keep it intact and extend it rather than bypassing it.

## Forbidden actions

- Do not delete large folders, reset the repo, or force-push.
- Do not commit or push unless the user explicitly asks.
- Do not hard-code secrets or API keys anywhere.
- Do not remove mock/dev mode or working tests.
- Do not make hardware mandatory for development.
- Do not let LLM output directly control hardware (hardware commands come
  only from the session runner / dashboard, never from generated text).
- Do not add Docker/Kubernetes/cloud deployment.
- Do not invent long copyrighted museum text — use short placeholder
  educational text or the existing demo pack.

## Working style

- Inspect real signatures/source before patching; this repo has established
  interfaces (`BaseDetector`, `BaseSTT`, `BaseTTS`, `BaseHardware`).
- Keep mock/dev mode green: after any change run
  `python -m pytest -q` and `python -m atlas.app.main --run 3`.
- Dependency injection through the container; Pydantic models with
  `extra="forbid"` (update the model before adding YAML keys).
- Type hints, clear file names, beginner-maintainable code. No
  microservices, no over-engineering.
- No OS-specific hard-coded paths — use `pathlib`.
- On Windows, avoid `python -c` with brackets/underscores/dunders; write a
  temporary .py script instead.

## Known hardware notes

- **KY-016 RGB LED GPIO is broken on JetPack 6.x with pins 29/31/33. Use the
  EV3 status LED instead. Do not let KY-016 become critical path.**
- FeeTech FT5478M servo expects ~7.4 V — verify the PSU before enabling servo.
- Target board: Jetson Orin Nano now, Orin NX 16 GB planned (JetPack 6.x).
- Headset: Shokz OpenComm2 UC. Camera: USB UVC default, optional Arducam
  IMX477. Optional ReSpeaker XVF3800 mic array.
