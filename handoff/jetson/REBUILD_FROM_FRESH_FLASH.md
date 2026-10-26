# Rebuild ATLAS from a fresh Jetson flash

This guide applies only to an explicitly approved replacement/fresh flash.
Do not use it to repair a working demo or deploy an ordinary source change;
use the [source-only runbook](../DEPLOYMENT_RUNBOOK.md) instead. Read the
[October 26 handoff](../2026-10-26_TEAMMATE_HANDOFF.md) and
`ATLAS_JETSON_NX_SETUP_LOG.md` before changing NVIDIA packages. Existing private
configuration, credentials, model caches, and protected backups are not in Git.

## 1. Flash and boot

- Board: Seeed reComputer Super J401 with Jetson Orin NX 16 GB.
- Known image: Seeed JetPack 6.2 / L4T R36.4.3 reComputer Super image.
- Use an Ubuntu 22.04 x86_64 host and Seeed's mass-flash instructions.
- Complete first boot, networking, username, and SSH setup.
- Do not run a generic `sudo apt upgrade -y` on the Seeed image.

## 2. Clone the complete handoff

```bash
mkdir -p ~/atlas
git clone --single-branch --branch codex/camera-offline-demo-2026-10-25 \
  https://github.com/EmersonV32/ATLAS_School_Pilot_v1_Phase3_1.git \
  ~/atlas/ATLAS_School_Pilot_v1_Phase3_1
cd ~/atlas/ATLAS_School_Pilot_v1_Phase3_1/atlas
```

As of October 26 the continuation branch above contains later working fixes
that have not been promoted to `main`; root `atlas/` is the active runtime.
Confirm the intended reviewed revision before rebuilding. Historical code
must not be used for a fresh recovery. See
[`../../archive/README.md`](../../archive/README.md) for retained evidence and
the `snapshot/repository-pre-cleanup-2026-10-11` recovery tag; that tag is not
the current application release.

The install clone fetches the selected branch, not every experimental branch. Fetch
a specific research branch separately only when reviewing that work; do not
add it to normal device startup.

This is a fresh-install guide, not permission to rename an existing working
installation. The existing Jetson service path remains
`/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`. No repository cleanup
step changes that live path, its private configuration, or its service.

Before installing anything, verify that the clone contains the complete
recovery bundle:

```bash
python scripts/verify_recovery_bundle.py
python scripts/verify_repository_layout.py
```

## 3. Bootstrap the current runtime

```bash
chmod +x scripts/*.sh
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

An optional school profile must be recreated separately using
[`../../atlas/docs/SCHOOL_WIFI_SETUP.md`](../../atlas/docs/SCHOOL_WIFI_SETUP.md).
Its private camera header and the Jetson NetworkManager profile are not Git
recovery artifacts. Do not assume authentication or camera-to-Jetson access
will work on a different network without testing it.

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
5. One English and one configured secondary-language spoken question complete
   STT -> retrieval/Gemini -> TTS. Include Traditional Chinese when it is part
   of the intended demonstration.
6. `sha256sum -c models/manifest.sha256` validates the committed YOLO model.
7. `python scripts/verify_recovery_bundle.py` confirms that recovery-critical
   files are tracked and private/generated artifacts are not tracked.
8. The GitHub `ATLAS recovery gate` passes for the commit being restored.

## Deliberately excluded private/generated state

- `.env`, API keys, Wi-Fi credentials, SSH private keys.
- XIAO `wifi_secrets.h` / `wifi_school_secrets.h` and private Jetson network
  profiles; recreate locally without recording passwords in documentation.
- Visitor runtime logs and generated Chroma/SQLite indexes.
- `atlas_yolo.engine` and `atlas_yolo.onnx`, regenerated on the target stack.
- `silero_vad.onnx`, downloaded and hash-verified by `restore_models.sh`.

These exclusions prevent credential leaks and stale device artifacts; they do
not remove the ability to reproduce the system.
