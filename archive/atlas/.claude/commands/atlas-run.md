Run the ATLAS mock pipeline end-to-end: `python -m atlas.app.main --run 3`
(dev mode, no hardware, no API key). Confirm 3 clean cycles: detection,
transcript, retrieval, dialogue, TTS print, hardware mock output. If a cycle
fails, capture the error, inspect `src/atlas/pipeline/session_runner.py` and
the failing component, and report the root cause before changing anything.
