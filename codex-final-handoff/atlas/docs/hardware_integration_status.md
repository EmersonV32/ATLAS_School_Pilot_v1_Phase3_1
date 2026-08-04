# ATLAS hardware integration status

Updated 2026-08-02 for the Seeed reComputer Super J401 with Jetson Orin NX
16 GB, JetPack 6.2 / Seeed L4T R36.4.3.

## Installed on the Jetson

- Project: `~/atlas/ATLAS_School_Pilot_v1_integrated`
- Environment: `~/atlas/venvs/atlas-school-pilot`
- YOLO weights: `models/atlas_yolo.pt`
- TensorRT engine: `models/atlas_yolo.engine` (FP16, active by default)
- Piper voices: `~/piper_voices`
- Silero VAD: `models/silero_vad.onnx`
- RAG: 143 grounded chunks for seven artworks
- Tests: 157 passed (one unrelated Starlette deprecation warning)

Run the read-only hardware check:

```bash
cd ~/atlas/ATLAS_School_Pilot_v1_integrated
./scripts/preflight_device.sh
```

When all hardware is connected, also open the configured camera:

```bash
./scripts/preflight_device.sh --open-camera
```

Start ATLAS. It preloads everything, prints a status table, and waits for
Enter before it begins:

```bash
./scripts/start_device.sh
```

## Physical checkpoint 1: Shokz OpenComm2 UC

1. Plug the Shokz Loop USB dongle into a Jetson USB port (use the supplied
   USB-C/USB-A adapter if needed).
2. Turn on the headset and wait for its connected announcement.
3. Run `./scripts/preflight_device.sh`.
4. `Shokz audio` must report OK. The software searches Shokz, OpenComm, and
   Loop names, so Linux card-number changes after reboot do not matter.

## XIAO ESP32-S3 Sense camera: completed

- Firmware: `firmware/xiao_camera`
- Board/core: XIAO ESP32-S3, Espressif Arduino core 3.3.11
- Build options: OPI PSRAM and 8 MB maximum application partition
- Controls: `http://atlas-camera.local`
- Stream: `http://atlas-camera.local:81/stream`
- Native stream: 640x480 JPEG quality 10, latest-frame buffering, Wi-Fi sleep disabled
- Verified throughput from Jetson: 23.62 FPS (22.75 FPS with desktop rendering)
- Sustained YOLO inference on Orin NX: 40.6 ms median at `imgsz=416`

The camera announces `atlas-camera.local` with mDNS, so a DHCP address change
does not require editing ATLAS. `config/settings.yaml` is already configured to
use this hostname. Run a live check with:

```bash
./scripts/preflight_device.sh --open-camera
```

To change Wi-Fi later, connect the XIAO to the Windows setup computer and run
`firmware/xiao_camera/configure_wifi.ps1`, enter the new 2.4 GHz credentials,
put the board in bootloader mode, and run `build_and_flash.ps1`. The generated
`wifi_secrets.h` is ignored by Git.

### Camera physical checkpoint (2026-08-01)

- The camera, Sense expansion board, ribbon cable, and U.FL antenna were
  visually checked and are assembled correctly.
- The supplied heatsink is still **not installed**. Even one half blocks the
  nearby BAT pads when it properly covers the gold Thermal PAD.
- Leave the blue adhesive liners attached. Connect/solder the future battery
  leads to BAT+ and BAT- before installing the heatsink.
- A protected 3.7 V LiPo around 800-1000 mAh is the preliminary target for
  2-3 hours, but measure real current and mounting space before purchasing.
- A post-handling device preflight received a fresh frame successfully.
- During a live trial the detector recognized Tutankhamun's mask at roughly
  50-90% confidence near the center.

## Listening cue and full interaction: completed

The first full interaction trial exposed a usability problem: Whisper opened
a five-second recording window silently, so the visitor could not know when
to speak. ATLAS now plays a short, language-neutral two-note cue immediately
before microphone capture.

Changed components:

- `BaseTTS.cue()` shared interface
- `PiperTTS.cue()` generated WAV and Shokz playback
- `MockTTS.cue()` test/dev implementation
- `SessionRunner` cue immediately before `stt.listen()`
- Deepgram connection preparation before the cue, so first words are not clipped
- `scripts/test_listening_cue.py` standalone hardware check

Verification on the Jetson:

```text
Listening cue playback succeeded
157 passed, 1 non-blocking Starlette deprecation warning
```

Two complete camera -> gaze trigger -> cue -> Shokz question -> Whisper -> RAG
-> answer -> Piper cycles were completed successfully. One used the mock LLM
and one used real Gemini. The Mona Lisa was detected at 86-97%, the centered
hold triggered in about 2.0-2.1 seconds, and both sessions exited cleanly.

The Shokz player now selects the named PulseAudio output and falls back to raw
ALSA only when needed. This prevents the previous `Device or resource busy`
failure. Capture selection also ignores PulseAudio `.monitor` pseudo-sources,
so preflight reports the actual Shokz mono microphone.

RAG is initialized on the runtime's owning thread during preload. This fixes
the SQLite cross-thread error exposed by the first complete interaction test.

## Streaming speech and dialogue upgrade

- STT: Deepgram Nova-3 multilingual streaming, with local Silero VAD ending
  the question after real speech and silence rather than a fixed wait.
- TTS: Cartesia Sonic 3.5 streams 24 kHz PCM directly to the Shokz output.
- Resilience: local Whisper and Piper are preloaded as offline fallbacks.
- Dialogue: Gemini tokens are assembled into complete sentences; each grounded
  sentence can begin TTS while Gemini continues generating the next one.
- Startup: camera, TensorRT, RAG/embedding model, both speech paths, and the
  Gemini SDK client load before the terminal says ATLAS is ready.

The Deepgram and Cartesia keys are intentionally not in Git. Enter them in a
Jetson terminal with hidden input:

```bash
cd ~/atlas/ATLAS_School_Pilot_v1_integrated
./scripts/configure_cloud_keys.sh
./scripts/preflight_device.sh
```

## Vision latency and manual correction

- The FP16 TensorRT engine produced a 14.31 ms median wall time versus
  37.52 ms for PyTorch on the live camera, a 2.62x speedup.
- A three-artwork parity check produced the same correct detection with both
  backends and a 3.13x median speedup.
- Press `c` then Enter, or say the translated equivalent of "capture this
  artwork", to send only the in-memory centre crop to Gemini for correction.
- The future Shokz multifunction-button integration can call
  `DeviceRuntime.request_manual_capture()`; no Linux button event has yet been
  confirmed for the dongle.

## RAG content upgrade

The index contains 143 short, museum-sourced chunks. Existing sheets for Mona
Lisa, The Starry Night, and Tutankhamun's mask were expanded, and these four
works were added:

- Sunflowers
- Liberty Leading the People
- Girl with a Pearl Earring
- The Great Wave off Kanagawa

English and French have native content. Spanish and Italian questions fall
back to grounded English chunks, while the LLM answers in the detected visitor
language. `scripts/evaluate_rag.py` currently passes 9/9 detailed retrieval
checks. The four new works are available through RAG and manual capture now;
automatic YOLO recognition needs approved labeled training images first.

## Current cloud status

The integrated repo has a private `.env` with mode `600`; the API key value is
not recorded here. Cloud use remains opt-in through `ATLAS_LLM_PROVIDER=gemini`
and `ATLAS_CLOUD_LLM_ENABLED=true`. A single authorized Gemini interaction was
successful on 2026-08-02.

The retired `google-generativeai` dependency was replaced by the supported
`google-genai` SDK. Offline fake-client coverage verifies Gemini request
construction without spending quota. The migration passed the full test suite;
no second cloud call was made after migration.

Gemini is configured and its manual-capture path has been verified. Deepgram
and Cartesia code, dependencies, local fallbacks, and tests are ready, but their
two private API keys still need to be entered before live cloud speech testing.

The requested new user/admin dashboard has not been started. Its requirements
and permission must be confirmed after the runtime integration is accepted.

## Physical checkpoint 3: EV3 stands

1. Upload `ev3/ev3_motors.py` to the EV3 and run it.
2. Connect Starry Night to EV3 port A, Mona Lisa to B, and the mask to C.
3. Pair and trust the EV3 from the Jetson with `bluetoothctl`. The last known
   brick address was `2C:6B:7D:7B:AE:02`; confirm it before using it.
4. Enable it for one terminal session:

```bash
export ATLAS_ENABLE_EV3=true
export ATLAS_EV3_ADDRESS="2C:6B:7D:7B:AE:02"
./scripts/start_device.sh
```

The exhibit starts with all artworks up. Holding a centered artwork for two
seconds leaves that artwork up and lowers the other two. After ATLAS finishes
speaking, all three return up.

## Physical checkpoint 4: Gemini

Create `~/atlas/ATLAS_School_Pilot_v1_integrated/.env` containing only:

```text
GEMINI_API_KEY=your_real_key_here
```

Never commit that file. Enable cloud answers for a run with:

```bash
export ATLAS_LLM_PROVIDER=gemini
export ATLAS_CLOUD_LLM_ENABLED=true
./scripts/start_device.sh
```

Without both switches, ATLAS intentionally keeps the mock model active.

## Safety notes

- Do not run `sudo apt upgrade -y` on this Seeed image. Critical NVIDIA L4T
  packages are held because a generic NVIDIA upgrade previously broke dpkg.
- The old repo and `yolo-runtime` environment remain untouched.
- No raw camera frames or microphone recordings are saved.
