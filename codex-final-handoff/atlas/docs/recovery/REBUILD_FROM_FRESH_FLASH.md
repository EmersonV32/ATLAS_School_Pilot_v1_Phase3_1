# Rebuild ATLAS from a fresh Jetson flash

This is the shortest authoritative recovery path. Read
`ATLAS_JETSON_NX_SETUP_LOG.md` before changing NVIDIA packages.

## 1. Flash and boot

- Board: Seeed reComputer Super J401 with Jetson Orin NX 16 GB.
- Known image: Seeed JetPack 6.2 / L4T R36.4.3 reComputer Super image.
- Use an Ubuntu 22.04 x86_64 host and Seeed's mass-flash instructions.
- Complete first boot, networking, username, and SSH setup.
- Do not run a generic `sudo apt upgrade -y` on the Seeed image.

## 2. Clone the complete handoff

```bash
mkdir -p ~/atlas
git clone https://github.com/EmersonV32/ATLAS_School_Pilot_v1_Phase3_1.git \
  ~/atlas/ATLAS_School_Pilot_v1_Phase3_1
cd ~/atlas/ATLAS_School_Pilot_v1_Phase3_1/codex-final-handoff/atlas
```

`codex-final-handoff/atlas` is the authoritative integrated runtime. The
repository's `archive/atlas/` folder is an earlier application snapshot and
must not be used for a fresh recovery. The old nationals code, dataset,
training runs, and weights are under `../legacy/nationals_2026`; they are
reference/fallback material, not the current runtime.

Before installing anything, verify that the clone contains the complete
recovery bundle:

```bash
python scripts/verify_recovery_bundle.py
```

## 3. Bootstrap the current runtime

```bash
chmod +x scripts/*.sh scripts/recovery/*.sh
./scripts/bootstrap_jetson.sh
```

This creates `~/atlas/venvs/atlas-school-pilot`, installs the captured Jetson
Python stack, verifies/downloads models, downloads Piper voices, primes
Whisper/embedding caches, exports TensorRT, ingests RAG, runs tests, and
installs the user service.

## 4. Restore secrets without Git

```bash
cp .env.example .env
chmod 600 .env
./scripts/configure_cloud_keys.sh
```

Add `GEMINI_API_KEY` to `.env` with a local editor. Never commit `.env`.
Reflash recovery also requires entering XIAO Wi-Fi credentials through
`firmware/xiao_camera/configure_wifi.ps1`; `wifi_secrets.h` is intentionally
not in Git.

## 5. Connect and verify hardware

```bash
./scripts/preflight_device.sh --open-camera
python scripts/test_silero_vad.py
python scripts/evaluate_rag.py
python -m pytest -q
```

Expected core hardware: Shokz OpenComm2 UC/Loop120 dongle and the XIAO
ESP32-S3 Sense stream at `http://atlas-camera.local:81/stream`. EV3 is optional
until the artwork stand is connected.

## 6. Start ATLAS

```bash
systemctl --user start atlas.service
systemctl --user status atlas.service --no-pager
tail -f data/logs/atlas-runtime.log
```

Dashboard: `http://127.0.0.1:8765/admin` on the Jetson itself.

## Recovery acceptance gate

A recovery is not complete until all of these are true:

1. `python -m pip check` reports no broken requirements.
2. `python -m pytest -q` passes.
3. `./scripts/preflight_device.sh --open-camera` has no critical failure.
4. The admin dashboard shows live camera and runtime logs.
5. One English and one French spoken question complete STT -> RAG -> Gemini -> TTS.
6. `sha256sum -c models/manifest.sha256` validates the committed YOLO model.
7. `python scripts/verify_recovery_bundle.py` confirms that recovery-critical
   files are tracked and private/generated artifacts are not tracked.
8. The GitHub `ATLAS recovery gate` passes for the commit being restored.

## Deliberately excluded private/generated state

- `.env`, API keys, Wi-Fi credentials, SSH private keys.
- Visitor runtime logs and generated Chroma/SQLite indexes.
- `atlas_yolo.engine` and `atlas_yolo.onnx`, regenerated on the target stack.
- `silero_vad.onnx`, downloaded and hash-verified by `restore_models.sh`.

These exclusions prevent credential leaks and stale device artifacts; they do
not remove the ability to reproduce the system.
