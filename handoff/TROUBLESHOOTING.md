# ATLAS troubleshooting

Work top-down: dev mode first, then one real adapter at a time (see
`operations/DEVICE_DEMO_CHECKLIST.md`).

## Dev mode / general

| Symptom | Fix |
|---|---|
| `pytest` fails after a change | Run `python -m pytest -q` and read the first failure; dev mode must stay green before device work. |
| `--run 3` prints `no cycle: no_detection` | MockDetector exhausted or tracker rejected an unknown artwork_id — re-ingest the pack so artwork IDs match. |
| Retriever returns nothing | Re-ingest: `python -m atlas.rag.ingest --pack data/content_packs/demo_pack --mode dev --reset`. Check chunk `language` and `educational_level` match the query; unknown levels fall back to `adult_beginner`. |
| Settings validation error on startup | A YAML key has no matching field — settings use `extra="forbid"`. Add the field to `src/atlas/config/settings.py` first. |

## Gemini

| Symptom | Fix |
|---|---|
| "GEMINI_API_KEY is not set" | Put the key in `.env` (never in code/YAML). PowerShell for one session: `$env:GEMINI_API_KEY='...'`. |
| Mock answers in demo mode | All three must hold: `llm.provider: gemini`, `llm.cloud_llm_enabled: true`, key set. This is deliberate (cloud disclosure). |
| "google-generativeai is not installed" | `pip install -e ".[llm]"`. |
| Timeouts | Check network; `llm.timeout_s` default is 8 s. ATLAS falls back to a safe apology answer — cycles never hang the pipeline. |

## Whisper (STT)

| Symptom | Fix |
|---|---|
| "faster-whisper not installed" | `pip install -e ".[audio]"` (plus `sounddevice`, `numpy` for the mic path). |
| No transcript captured | Check the Shokz OpenComm2 UC is the default input device; speak within `listen_duration_s` (5 s). ATLAS asks to repeat; use the dashboard typed-question fallback meanwhile. |
| Slow on Jetson | Use `whisper_model_size: tiny` (Orin Nano) or `small` (Orin NX), `whisper_compute_type: int8`. |

## Piper (TTS)

| Symptom | Fix |
|---|---|
| "Piper binary not found on PATH" | Install piper or set `hardware.piper_binary_path`. |
| Silent output | Voice `.onnx` files must exist at `piper_voice_en` / `piper_voice_fr`; check `aplay` works (Linux). |
| TTS fails mid-demo | Not fatal: the answer text still appears on the dashboard and `tts_fallback_used` is logged. |

## YOLO (vision)

| Symptom | Fix |
|---|---|
| "ultralytics not installed" | `pip install -e ".[vision]"`. |
| Model file missing | Train/export weights and set `hardware.yolo_model_path`. |
| Wrong artwork detected | Check the label→artwork_id mapping in `vision/yolo_detector.py`; the tracker logs "Detected unknown artwork_id" when a label has no matching pack entry. Use the dashboard manual override during the visit. |
| Flickering detection | The tracker needs 3 consecutive frames to declare stable and falls back to the last stable artwork on low confidence — this is expected smoothing. |

## EV3 / hardware

| Symptom | Fix |
|---|---|
| EV3 connect failed | Pair first (`bluetoothctl` → pair/trust), set `hardware.ev3_bt_address`, `enable_ev3: true`, run in device mode. |
| Stand doesn't move | Check the emergency stop is not latched (dashboard health panel); clearing requires the admin token. |
| Status LED dead on Jetson GPIO | **Known issue:** the KY-016 RGB LED GPIO is broken on JetPack 6.x with pins 29/31/33. Use the EV3 status LED instead — the KY-016 is not critical path. Do not spend demo time on it. |
| Servo jitter / brownout | FeeTech FT5478M expects ~7.4 V — verify the PSU before `enable_servo: true`. |

## Dashboard

| Symptom | Fix |
|---|---|
| Admin buttons return 401/503 | 503: set `ATLAS_ADMIN_TOKEN` in the server environment. 401: paste the same token into the dashboard's Admin token field. |
| Port already in use | `--port 8766` (any free local port). |
| Opened from another device | By design the server binds 127.0.0.1. Keep it local. |
