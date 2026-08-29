Walk the ATLAS device-demo validation ladder from
`../../../handoff/operations/DEVICE_DEMO_CHECKLIST.md`. Check which optional dependencies are
installed (`google-generativeai`, `faster-whisper`, `piper-tts`,
`ultralytics`, `chromadb`) and which env vars/paths are configured
(GEMINI_API_KEY set? yolo_model_path exists? piper voices exist?). Then
recommend the highest ladder stage (A–F) the machine can run right now and
the exact command to run it. Never make hardware required for dev mode, and
remember: KY-016 RGB LED GPIO is broken on JetPack 6.x — use the EV3 status
LED, it is not critical path.
