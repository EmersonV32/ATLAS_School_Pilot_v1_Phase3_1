# ATLAS device demo checklist

Climb the ladder one rung at a time. Each stage must run clean before the
next. Dev mode (all mocks) must stay green at every point:
`python -m pytest -q && python -m atlas.app.main --run 3`.

Target hardware: Jetson Orin Nano (now) / Orin NX 16 GB (planned),
JetPack 6.x, USB UVC camera (optional Arducam IMX477), Shokz OpenComm2 UC
headset (optional ReSpeaker XVF3800), optional EV3 stand.

## Validation ladder

| Stage | Real | Mock | Preconditions |
|-------|------|------|---------------|
| A | Gemini + RAG | vision, STT, TTS, EV3 | `.[llm]` installed, `GEMINI_API_KEY`, `cloud_llm_enabled: true`, pack ingested |
| B | Piper + Gemini + RAG | vision, STT, EV3 | + piper binary, EN/FR `.onnx` voices at configured paths |
| C | Whisper + Gemini + RAG | vision, Piper, EV3 | + `.[audio]`, mic detected, `whisper_model_size` fits the board |
| D | YOLO + RAG | dialogue, audio, EV3 | + `.[vision]`, trained weights at `yolo_model_path`, labels map to artwork_ids |
| E | YOLO + Whisper + Gemini | Piper, EV3 | stages C and D pass |
| F | Full system + Piper + EV3 | — | + EV3 paired, `ev3_bt_address`, `enable_ev3: true` |

For each stage:

1. Set `config/settings.yaml` mode (`demo` for A–C, `device` for D–F).
2. Run 3 cycles: `python -m atlas.app.main --run 3` → all clean.
3. Run 10 cycles: `python -m atlas.app.main --run 10` → all clean.
4. 30-minute stability test: repeat cycles for 30 min (script or loop),
   watching memory and latency.
5. Capture logs from `data/logs/` and file issues. **Fix only critical
   bugs** before moving on.

## Reminders

- Hardware is never required for development; every adapter fails
  gracefully back to a mock-friendly behaviour.
- The KY-016 RGB LED GPIO is broken on JetPack 6.x (pins 29/31/33). Use the
  EV3 status LED. Not critical path — do not debug it during a demo.
- FeeTech FT5478M servo expects ~7.4 V; verify the PSU before
  `enable_servo: true`.
- Emergency stop: dashboard red button latches all movement off; clearing
  requires the admin token.
- Cloud LLM stages (A+) send question text + retrieved excerpts to Gemini —
  confirm the school has seen docs/cloud_llm_disclosure.md first.
