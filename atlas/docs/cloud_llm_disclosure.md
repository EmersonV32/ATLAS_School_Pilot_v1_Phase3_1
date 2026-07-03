# Cloud LLM disclosure

ATLAS uses an edge-first architecture: vision, speech, retrieval, motor
control, and text-to-speech run locally or nearby, while the current
prototype uses a cloud language model for final response generation. A
future version aims to replace this with an on-device language model.

ATLAS is **not** fully offline and does not claim to be.

## When cloud calls happen

A cloud LLM call is made only when **all** of these are true:

1. `config/settings.yaml` sets `llm.provider: gemini`
2. `config/settings.yaml` sets `llm.cloud_llm_enabled: true`
3. The `GEMINI_API_KEY` environment variable is set
4. ATLAS runs in `device` or `demo` mode

In `dev` and `local` modes, and whenever any condition above is not met,
ATLAS uses a deterministic mock LLM and **no data leaves the machine**.

## What is sent to the cloud (Google Gemini)

- The visitor's question text (after prompt-injection filtering)
- Short retrieved excerpts from the school-approved content pack
- The ATLAS system instructions (language, profile, answer rules)

## What is never sent

- Audio recordings (speech is transcribed locally by Whisper)
- Camera images or video (detection runs locally with YOLO)
- Student names (never collected), session IDs, or telemetry logs
- API keys of other services

## Safeguards on cloud answers

Answers must return in a structured JSON contract and pass grounding
validation (cited chunk IDs must exist in the retrieved context, and
unsupported claims force a safe refusal) plus a content safety filter —
**before** anything is spoken. Hallucinations are made less likely and less
harmful by this pipeline, but no system can make them impossible; that is
why refusal is the default when verification fails.
