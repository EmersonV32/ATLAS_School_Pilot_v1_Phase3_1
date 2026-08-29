# ATLAS teacher guide

*Atlas — because every story deserves a listener.*

ATLAS is a teacher-controlled educational AI platform: a wearable AI museum
guide that identifies what a student is looking at and answers questions in
the student's language and level. You control it from a local dashboard.

## Starting the dashboard

Ask your technical contact to run, on the ATLAS laptop:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn atlas.dashboard.api:app --host 127.0.0.1 --port 8765
```

Then open **http://127.0.0.1:8765** in a browser on the same machine. The
dashboard is local only — it is not on the internet.

## Running a class session

1. **Start session** — press *Start session*. The session ID shown is
   anonymous; ATLAS never asks for or stores student names.
2. **Experience Settings** — choose the content pack, language (English and
   French are fully supported; Spanish/Italian are demo-level), and profile
   (child, teen, adult beginner, expert, visual impairment, simple
   language). *Accessibility mode* switches to rich audio descriptions of
   shape, colour and composition. Press **Apply**.
3. **Artwork Context** — shows what ATLAS currently thinks the student is
   looking at, with confidence and stable/unstable state.
   - If detection is wrong or the camera is unavailable, pick the artwork in
     **Manual override** and press *Set override*. Clear it when done.
4. **Ask ATLAS** — the typed-question fallback. If the microphone fails or a
   student prefers typing, type the question and press *Ask*. The answer is
   shown on screen with grounding and confidence indicators.
5. **Stop session** when the class ends.

## What the indicators mean

- **grounded=true** — the answer came from verified content pack sources.
- **fallback=true** — ATLAS could not verify an answer and said so instead
  of guessing. This is correct behaviour, not an error.
- **Detection: unstable** — ATLAS has not seen the same artwork for enough
  camera frames yet; wait a moment or use manual override.

## Privacy at a glance (see docs/privacy_summary.md)

- No raw audio, no photos/video, no face recognition, no student names.
- Anonymous session IDs; transcripts are **not** logged by default.
- The Privacy panel on the dashboard shows the live settings.
- Cloud LLM: when enabled, the question text and retrieved artwork notes are
  sent to Google Gemini to compose the final answer (see
  docs/cloud_llm_disclosure.md). In dev/mock mode nothing leaves the laptop.

## If something goes wrong

- **Emergency stop** (red button) instantly blocks all stand movement. Only
  the operator with the admin token can clear it.
- Answers show "I don't have that detail verified…" — ATLAS refuses rather
  than inventing facts. Ask a different question or add content to the pack.
- More help: docs/troubleshooting.md.
