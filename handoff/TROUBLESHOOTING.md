# ATLAS troubleshooting

Current triage: October 26. Read the
[teammate handoff](2026-10-26_TEAMMATE_HANDOFF.md) first. Preserve the working
demo, reproduce one problem, then change one component. Laptop checks and
physical acceptance are separate. Do not dump visitor logs or secret files.

## Existing Jetson / demo

| Symptom | Safe next step |
| --- | --- |
| Laptop cannot open dashboard | Obtain today's Jetson IP with `hostname -I`; try `http://IP:8765/` and `/admin`. The reported hotspot IP was `192.168.137.193`, not a fixed address. Check public `/health` locally and selected user-service metadata. Use the SSH tunnel in the handoff if only loopback is reachable. |
| Service stopped or port occupied | Identify the current user service/process. Ask the operator before starting/restarting; never launch another Uvicorn or change ports to hide a duplicate runtime. |
| Start is unavailable | Confirm headset readiness and selected language/profile. The offline primary camera is not a conversation-start blocker. Refresh the browser for the current shell (v30 at last deployment). |
| Navigation ignores a tap | Refresh the versioned shell, reproduce without repeated clicks, and check whether the delayed-request fix is installed. See [navigation evidence](../atlas/docs/VISITOR_NAVIGATION_ACCEPTANCE.md). |
| Silent or changing voice | Inspect authenticated admin readiness and selected output/provider without exposing tokens. Confirm internet/headset routing, then test one short response. Cartesia retry/serialization fixes are installed, but provider quality requires audible acceptance. Do not edit voices/keys or restart repeatedly without a diagnosis. |
| ATLAS sounds like “ate las” | Last installed `4b2233c` normalizes the Cartesia speech payload to `Atlas`. Verify installation and listen to one introduction; the audible result was not yet reported. See [pronunciation record](../atlas/docs/CARTESIA_NAME_PRONUNCIATION.md). |
| Camera unavailable | Primary wearable camera has reported BAT+ damage and is offline. Use camera-free conversation/manual artwork context. The separate CSI preview is independent; don't flash or physically repair either during a software demo fix. |
| School networks absent | Keep the reported working Windows mobile-hotspot arrangement. Follow the network section in the current handoff; direct discovery remains unresolved. Home success, `country 00`, or one weak hotspot reading does not prove a driver/hardware fault. |
| Admin request returns 401 | Protected route is rejecting unauthenticated access as expected. Unlock locally with the privately held admin credential. A 503 can indicate unconfigured auth; don't disable auth or paste tokens into chat/shell. |
| SSH times out during deployment | Inspect the SAME transaction PID/result after reconnecting or use the local operator. Do not repeat apply, delete its lock, reboot, or restart networking. Follow the [deployment runbook](DEPLOYMENT_RUNBOOK.md). |
| SG90 does not move | Commissioning is paused with no successful motion. Keep normal pan and confirmations false. Do not repeat sweeps, clear safety gates, write registers, or substitute a voltage intended for another motor. |
| Buzzing, jitter, heat, smoke or repeated rebooting | Stop the experience; the present operator disconnects power safely. No software diagnosis overrides a physical fault. Do not automatically resume after clearing an emergency stop. |

Safe Jetson metadata (as `super-alex`):

```bash
hostname -I
systemctl --user show atlas.service -p ActiveState -p SubState -p NRestarts -p ExecMainStatus
curl --fail --max-time 5 http://127.0.0.1:8765/health
```

## Isolated laptop development only

The remaining examples apply to a fresh mock/dev checkout with no live private
environment or hardware. Package installs and configuration edits are not
routine repairs on the installed Jetson. Consult declared dependencies and
the [validation checklist](VALIDATION_CHECKLIST.md) before changing them.

## Dev mode / general

| Symptom | Fix |
|---|---|
| Tests fail after a change | Run `python scripts/run_deployment_pytest.py` with the Windows isolation guidance if needed; read the first failure. Do not use plain pytest on a configured machine. |
| `--run 3` prints `no cycle: no_detection` | MockDetector exhausted or tracker rejected an unknown artwork_id — re-ingest the pack so artwork IDs match. |
| Retriever returns nothing | Re-ingest: `python -m atlas.rag.ingest --pack data/content_packs/demo_pack --mode dev --reset`. Check chunk `language` and `educational_level` match the query; unknown levels fall back to `adult_beginner`. |
| Settings validation error on startup | A YAML key has no matching field — settings use `extra="forbid"`. Add the field to `src/atlas/config/settings.py` first. |

## Gemini

| Symptom | Fix |
|---|---|
| Provider key unavailable | Use mocks for development. Humans restore private access through the protected process; an agent must not read, paste, or edit live credentials. |
| Mock answers in demo mode | All three must hold: `llm.provider: gemini`, `llm.cloud_llm_enabled: true`, key set. This is deliberate (cloud disclosure). |
| Gemini client dependency missing | In the isolated dev venv, install the declared `llm` extra; do not guess a replacement SDK on the Jetson. |
| Timeouts | Check network; `llm.timeout_s` default is 8 s. ATLAS falls back to a safe apology answer — cycles never hang the pipeline. |

## Whisper (STT)

| Symptom | Fix |
|---|---|
| "faster-whisper not installed" | `pip install -e ".[audio]"` (plus `sounddevice`, `numpy` for the mic path). |
| No transcript captured | Check the Shokz OpenComm2 UC is the default input device; `listen_duration_s` defaults to 8 s. Whisper uses a fixed recording window; use the dashboard typed-question fallback meanwhile. |
| Slow on Jetson | Use `whisper_model_size: tiny` (Orin Nano) or `small` (Orin NX), `whisper_compute_type: int8`. |

## Deepgram (STT) — dated implementation context

The original listening workflow introduced an 8-second wait for speech
to begin, followed by capture for up to 45 seconds. Normal end-of-question silence is
2 seconds; clearly unfinished phrases get up to 4 seconds. These are source
defaults, not proof of deployment or guarantees for arbitrary pauses. See the
[workflow record](../atlas/docs/2026-10-11_CONVERSATION_LISTENING_STABILITY.md).

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

## Physical hardware

Use a separate approved task and the actual component's specification. Older
EV3, FeeTech, LED, or PCA9685 notes are not SG90 wiring instructions. Do not
enable a different actuator or bypass an emergency stop to remove an inactive
dashboard label. The current [pan record](../atlas/docs/CAMERA_PAN.md) and
teammate handoff preserve the stopped experiment and unresolved checks.
