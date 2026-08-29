# ATLAS architecture

> ATLAS uses an edge-first architecture: vision, speech, retrieval, motor
> control, and text-to-speech run locally or nearby, while the current
> prototype uses a cloud language model for final response generation. A
> future version aims to replace this with an on-device language model.

ATLAS is a wearable AI museum guide and cultural mediation system — adaptive
cultural mediation, not a chatbot. It identifies what a visitor is looking
at, answers in the visitor's language and level, and creates a personalized,
accessible cultural experience.

## Pipeline (one interaction cycle)

```
camera frame
  → VisionDetector (Mock / YOLO)         src/atlas/vision/
  → ArtworkTracker (stability, manual override, last-stable fallback)
  → STT (Mock / faster-whisper)          src/atlas/audio/
  → HybridRetriever                      src/atlas/rag/
      dense (Chroma / SimpleVectorStore)
      + keyword (SQLite FTS5 / BM25)
      → Reciprocal Rank Fusion (k=60)
      → heuristic reranker
      → level fallback (exact level → adult_beginner)
  → DialogueEngine                       src/atlas/dialogue/
      prompt-injection filter (refuse before LLM)
      → PromptBuilder (language + profile + chunk-tagged context)
      → LLM (MockLLMClient / GeminiClient, JSON contract)
      → GroundingValidator (+ unsupported-claims check)
      → SafetyFilter
  → TTS (Mock / Piper) — speaks only the validated answer
  → Hardware (Mock / EV3) — LED + stand rotation; emergency-stop latch
```

Orchestrated by `pipeline/session_runner.py`; every component is injected
through `app/dependency_container.py` and selected by run mode.

## Run modes

| Mode | Vision | STT/TTS | RAG | LLM | Hardware |
|------|--------|---------|-----|-----|----------|
| dev | mock | mock | real (SimpleVectorStore + FTS5) | mock | mock |
| local | mock | mock | real (Chroma) | mock | mock |
| demo | mock (fixed/override) | mock | real | Gemini* | mock |
| device | YOLO | Whisper/Piper | real | Gemini* | EV3 (opt-in) |

\* Gemini only when `llm.provider: gemini` **and** `llm.cloud_llm_enabled: true`
and `GEMINI_API_KEY` is set. Otherwise the mock LLM is used.

## Key design rules

- Mock/dev mode must always run with no hardware, no ML downloads, no keys.
- Hardware is optional and behind `BaseHardware`; motor commands pass through
  `send()`, which refuses while the emergency stop is latched. LLM output
  never controls hardware.
- Privacy defaults are safe: no raw audio/images/video, no face data, no
  student names, anonymous session IDs, transcripts not logged.
- Settings models use `extra="forbid"` — extend `config/settings.py` before
  adding YAML keys.

## Dashboard

`src/atlas/dashboard/` is a local FastAPI app (localhost only) used by the
teacher/operator: session control, experience settings, manual artwork
override, typed-question fallback, health, privacy panel, privacy-safe logs,
demo simulations, and emergency stop. See `docs/teacher_guide.md`.
