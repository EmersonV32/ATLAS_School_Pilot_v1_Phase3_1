# ATLAS Jetson NX Setup / Recovery Log

Date written: 2026-08-01  
Device: Seeed Studio reComputer Super / J401 Super carrier board with Jetson Orin NX 16GB  
Hostname: `super`  
Username: `super-alex`  
Jetson IP used during setup: `10.0.0.238`  

This file is a handoff/debug note for Claude, Codex, or another assistant. It records what was done to the Jetson after flashing, especially the apt/NVIDIA recovery workaround.

No private password or private SSH key is included here.

## Current Status

The Jetson is usable and boot-tested.

Confirmed after reboot:

```text
apt-get check: clean
dpkg --audit: clean
Root disk: /dev/nvme0n1p1, about 204G free at time of check
RAM: 15Gi total, about 13Gi available at idle
```

Important package state:

```text
nvidia-l4t-* critical packages are held and installed (`hi`)
```

Meaning:

- `h` = held, apt should not upgrade them
- `i` = installed/configured

Do not run this casually:

```bash
sudo apt upgrade -y
```

The Seeed J401 board had a known-style NVIDIA L4T package upgrade failure when apt tried to move kernel/bootloader packages from Seeed image 36.4.3 to NVIDIA repo 36.4.7.

## Important Version Mismatch

Current release file:

```text
/etc/nv_tegra_release says:
R36, REVISION: 4.3
Seeed Image Name mfi_recomputer-super-orin-nx-16g-j401-6.2-36.4.3-2025-05-22.tar.gz
branch R36.4.3
```

Current running kernel after recovery:

```text
Linux super 5.15.148-tegra #1 SMP PREEMPT Thu Sep 18 15:08:33 PDT 2025 aarch64
```

So the system reports Seeed 36.4.3 in `/etc/nv_tegra_release`, but is running a 36.4.7 kernel package. This came from the partial apt upgrade. Since it boots, apt is clean, and packages are held, we chose to proceed instead of reflashing.

## What Went Wrong

User accidentally ran:

```bash
sudo apt update
sudo apt upgrade -y
```

The upgrade tried to configure NVIDIA packages:

- `nvidia-l4t-bootloader`
- `nvidia-l4t-kernel`
- `nvidia-l4t-kernel-dtbs`
- `nvidia-l4t-kernel-headers`
- `nvidia-l4t-kernel-oot-headers`
- `nvidia-l4t-kernel-oot-modules`
- `nvidia-l4t-display-kernel`
- `nvidia-l4t-jetson-io`

The failing error was:

```text
ERROR. 3767-000-0000--1--recomputer-orin-super-j401- does not match any known boards.
```

This left packages in broken states like `iF` and `iU`, later `hF` and `hU` after holds were applied.

## Recovery Workaround Applied

Because reflashing was very inconvenient and the Jetson still booted/SSH worked, we used a no-reflash dpkg recovery.

User explicitly approved:

```text
I approve the no-op dpkg recovery
```

Recovery script location used on Jetson:

```text
/tmp/repair_l4t_j401.sh
```

What the script did:

1. Backed up the failing maintainer scripts if backup did not already exist:

```bash
sudo cp /var/lib/dpkg/info/nvidia-l4t-bootloader.postinst /var/lib/dpkg/info/nvidia-l4t-bootloader.postinst.atlas-bak
sudo cp /var/lib/dpkg/info/nvidia-l4t-kernel.postinst /var/lib/dpkg/info/nvidia-l4t-kernel.postinst.atlas-bak
```

2. Replaced only these two post-install scripts with no-op success scripts:

```bash
/var/lib/dpkg/info/nvidia-l4t-bootloader.postinst
/var/lib/dpkg/info/nvidia-l4t-kernel.postinst
```

Replacement content:

```sh
#!/bin/sh
exit 0
```

3. Ran:

```bash
sudo dpkg --configure -a
```

4. Re-held critical NVIDIA L4T packages:

```bash
sudo apt-mark hold \
  nvidia-l4t-bootloader \
  nvidia-l4t-kernel \
  nvidia-l4t-kernel-dtbs \
  nvidia-l4t-kernel-headers \
  nvidia-l4t-kernel-oot-headers \
  nvidia-l4t-kernel-oot-modules \
  nvidia-l4t-display-kernel \
  nvidia-l4t-jetson-io \
  nvidia-l4t-core \
  nvidia-l4t-initrd
```

5. Rebooted and verified SSH came back.

Post-reboot checks passed:

```bash
sudo apt-get check
sudo dpkg --audit
```

## Current Held NVIDIA Packages

At time of setup, `apt-mark showhold | grep nvidia-l4t` showed:

```text
nvidia-l4t-bootloader
nvidia-l4t-core
nvidia-l4t-display-kernel
nvidia-l4t-initrd
nvidia-l4t-jetson-io
nvidia-l4t-kernel
nvidia-l4t-kernel-dtbs
nvidia-l4t-kernel-headers
nvidia-l4t-kernel-oot-headers
nvidia-l4t-kernel-oot-modules
```

Do not unhold these unless you are intentionally fixing/reflashing the Seeed Jetson image.

## SSH Access Set Up For Codex

Codex created a local SSH key on the Windows machine:

```text
C:\Users\zhupo\Documents\Codex\2026-05-24\files-mentioned-by-the-user-atlas\ssh_key\atlas_codex_jetson
```

Public key installed into Jetson:

```text
~/.ssh/authorized_keys
```

This allowed passwordless SSH for Codex from this Windows/Codex environment.

Do not publish the private key. If needed, it can be removed from the Jetson by editing:

```bash
nano ~/.ssh/authorized_keys
```

and deleting the line ending in:

```text
codex-atlas-jetson
```

## Base Packages Installed

Installed via apt after recovery:

```bash
sudo apt-get install -y \
  git git-lfs \
  python3-pip python3-venv python3-dev \
  build-essential cmake curl wget unzip \
  ffmpeg portaudio19-dev v4l-utils \
  bluetooth bluez alsa-utils
```

Notes:

- `pulseaudio-utils` was not available in this image, so it was skipped.
- Installing `portaudio19-dev` replaced `libjack-jackd2-0` with `libjack0`. Apt accepted this and `apt-get check` remained clean.
- `ffmpeg` came from NVIDIA L4T Jetson FFmpeg repo as `7:4.4.2-nvidia`.

## User Groups Added

The `super-alex` user was added to available hardware groups:

```text
dialout
video
audio
plugdev
render
input
bluetooth
gpio
i2c
```

Observed group list later included:

```text
super-alex adm dialout cdrom sudo audio dip video plugdev input render bluetooth i2c lpadmin gdm gpio weston-launch sambashare
```

If permissions seem weird, log out/in or reboot so group changes apply everywhere.

## Repos Cloned

Project base:

```text
~/atlas
```

Old stable repo:

```bash
git clone https://github.com/alexwithadog/wrofutureinnovators2026.git
```

Location:

```text
~/atlas/wrofutureinnovators2026
```

Commit at setup:

```text
1e7dc02
```

Confirmed files:

```text
JRAG2.py
requirements.txt
best.pt        about 20M
yolo26n.pt     about 5.3M
```

New Emerson repo:

```bash
git clone https://github.com/EmersonV32/ATLAS_School_Pilot_v1_Phase3_1.git
```

Location:

```text
~/atlas/ATLAS_School_Pilot_v1_Phase3_1
```

Commit at setup:

```text
20d3636
```

Confirmed files:

```text
~/atlas/ATLAS_School_Pilot_v1_Phase3_1/atlas/pyproject.toml
~/atlas/ATLAS_School_Pilot_v1_Phase3_1/atlas/requirements.txt
```

## Python Virtual Environment

Created:

```text
~/atlas/venvs/yolo-runtime
```

Command used:

```bash
python3 -m venv --system-site-packages ~/atlas/venvs/yolo-runtime
```

Activation:

```bash
source ~/atlas/venvs/yolo-runtime/bin/activate
```

Python:

```text
Python 3.10.12
```

## Python Packages Installed

Important manually chosen Jetson-compatible versions:

```text
torch 2.8.0
torchvision 0.23.0
numpy 1.26.4
opencv-python 4.10.0.84
scipy 1.11.4
ultralytics 8.4.115
faster-whisper 1.2.1
piper-tts 1.6.0
google-genai 2.16.0
chromadb 1.5.9
sentence-transformers 5.6.1
sounddevice 0.5.5
```

Torch install source:

```bash
python -m pip install torch==2.8.0 torchvision==0.23.0 \
  --index-url https://pypi.jetson-ai-lab.io/jp6/cu126
```

Important: an attempted install of latest Torch from the same index pulled `torch 2.11.0`, but it failed to import because:

```text
ImportError: libcudss.so.0: cannot open shared object file
```

So Torch was downgraded to `2.8.0`, which worked.

Also important: `ultralytics` initially pulled `numpy 2.2.6` and `opencv-python 5.0.0.93`, but Torch warned about NumPy 2 and `opencv-python 5` required NumPy 2. We fixed this by installing:

```bash
python -m pip uninstall -y opencv-python
python -m pip install --force-reinstall 'numpy==1.26.4' 'opencv-python==4.10.0.84'
python -m pip install --upgrade 'scipy==1.11.4'
```

Final check:

```bash
python -m pip check
```

Result:

```text
No broken requirements found.
```

## Verified Python Stack

The following imports/tests were successful in `~/atlas/venvs/yolo-runtime`:

```text
numpy 1.26.4
cv2 4.10.0
torch 2.8.0
torchvision 0.23.0
ultralytics 8.4.115
sounddevice 0.5.5
google.genai 2.16.0
faster_whisper 1.2.1
chromadb 1.5.9
sentence_transformers 5.6.1
langdetect ok
piper module ok
```

Torch CUDA test:

```text
torch.cuda.is_available(): True
GPU name: Orin
```

YOLO test:

```python
from ultralytics import YOLO
model = YOLO("best.pt")
```

Loaded class names:

```text
{0: 'mask_of_tutankhamun', 1: 'mona_lisa', 2: 'starry_night'}
```

RAG test:

```python
from atlas.rag import RAG
rag = RAG()
```

Loaded sheets:

```text
['mona_lisa', 'pharaoh_mask', 'starry_night']
```

## Piper Voices

Piper package installed, but voices were not present initially. The code expects:

```text
~/piper_voices
```

Downloaded voices:

```bash
python -m piper.download_voices --download-dir ~/piper_voices \
  en_US-ryan-low \
  fr_FR-siwis-medium \
  es_MX-claude-high \
  it_IT-paola-medium
```

Confirmed files:

```text
en_US-ryan-low.onnx
en_US-ryan-low.onnx.json
fr_FR-siwis-medium.onnx
fr_FR-siwis-medium.onnx.json
es_MX-claude-high.onnx
es_MX-claude-high.onnx.json
it_IT-paola-medium.onnx
it_IT-paola-medium.onnx.json
```

Piper synthesis test succeeded:

```bash
printf 'Hello, I am Atlas.\n' | python -m piper \
  --model en_US-ryan-low \
  --data-dir ~/piper_voices \
  --output-file /tmp/atlas_piper_test.wav
```

Generated:

```text
/tmp/atlas_piper_test.wav
```

The Piper CLI prints an ONNXRuntime GPU discovery warning, but synthesis still works:

```text
GPU device discovery failed ... /sys/class/drm/card1/device/vendor
```

This warning is not currently blocking Piper.

## Model Prewarm

Prewarmed/downloaded local heavy pieces:

```text
Whisper tiny CPU int8: ready in about 28s
RAG embedding model: ready in about 2.4s, 3 sheets
YOLO best.pt CUDA dummy inference: ready in about 1.26s
```

Whisper model:

```python
WhisperModel("tiny", device="cpu", compute_type="int8")
```

YOLO dummy inference:

```python
model = YOLO("best.pt")
model.to("cuda")
dummy = np.zeros((416, 416, 3), dtype=np.uint8)
model.predict(dummy, imgsz=416, verbose=False, device=0)
```

## Convenience Start Script

Created:

```text
~/atlas/start_atlas_old.sh
```

Content:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/atlas/wrofutureinnovators2026"
source "$HOME/atlas/venvs/yolo-runtime/bin/activate"
exec python JRAG2.py "$@"
```

Run old stable ATLAS:

```bash
~/atlas/start_atlas_old.sh
```

Manual environment:

```bash
cd ~/atlas/wrofutureinnovators2026
source ~/atlas/venvs/yolo-runtime/bin/activate
```

## Quick Command Note On Jetson

Created:

```text
~/atlas/JETSON_ATLAS_QUICK_COMMANDS.txt
```

It summarizes project locations, start command, and warnings.

## Performance

Jetson power mode at time of check:

```text
NV Power Mode: 40W
```

Ran once for current session:

```bash
sudo jetson_clocks
```

Note: `jetson_clocks` does not necessarily persist forever after reboot. Run it again while plugged into wall power before latency/performance tests.

## Hardware Checks

At time of check, no camera/mic/speaker/EV3 were connected.

Camera:

```text
ls /dev/video*: no /dev/video devices found
v4l2-ctl --list-devices showed only:
NVIDIA Tegra Video Input Device (platform:tegra-camrtc-ca):
    /dev/media0
```

Meaning: no USB camera was plugged in or recognized yet.

Audio capture:

```text
arecord -l showed Jetson Orin NX APE devices only
```

Audio playback:

```text
aplay -l showed HDMI devices and Jetson APE devices
```

Meaning: OpenComm / USB mic / speaker was not connected yet.

Next hardware tests after plugging things in:

```bash
ls /dev/video*
v4l2-ctl --list-devices
arecord -l
aplay -l
bluetoothctl
```

## Missing Runtime Pieces

Still missing / not configured:

1. Gemini API key:

```text
~/atlas/wrofutureinnovators2026/.env was missing
GEMINI_API_KEY was not set in shell
```

Need to create:

```bash
cd ~/atlas/wrofutureinnovators2026
nano .env
```

With:

```text
GEMINI_API_KEY=your_key_here
```

Do not commit `.env`.

2. Camera not connected/tested.

3. Mic/speaker/OpenComm not connected/tested.

4. EV3 Bluetooth not paired/tested on this new Jetson yet.

5. New Emerson repo not installed/tested beyond clone. Treat the old repo as the known-good baseline first.

## Recommended Next Steps

1. Plug in USB camera.

```bash
ls /dev/video*
v4l2-ctl --list-devices
```

2. Plug in mic/speaker or pair OpenComm.

```bash
arecord -l
aplay -l
bluetoothctl
```

3. Add `.env` with Gemini key.

4. Run:

```bash
~/atlas/start_atlas_old.sh
```

5. If ATLAS fails at camera/audio config, check constants near the top of:

```text
~/atlas/wrofutureinnovators2026/JRAG2.py
```

Likely things to adjust:

- camera index
- mic device index
- EV3 MAC address
- audio output command/device

## Critical Warnings

Do not run:

```bash
sudo apt upgrade -y
sudo apt autoremove
```

without thinking/checking first.

Before installing packages, it is safer to simulate:

```bash
sudo apt-get install -s package-name
```

Make sure it is not trying to remove or upgrade `nvidia-l4t-*`.

To check package health:

```bash
sudo apt-get check
sudo dpkg --audit
apt-mark showhold | grep nvidia-l4t
```

If apt/dpkg breaks again around NVIDIA packages, remember that the recovery workaround was intentionally applied to avoid reflashing, but reflashing remains the cleanest official reset path.

## 2026-08-01 Camera And Shokz Integration Update

- Shokz OpenComm2 UC input and output passed device preflight through the
  Loop120 USB dongle.
- XIAO ESP32-S3 Sense camera firmware was configured for the local 2.4 GHz
  network and announces `atlas-camera.local` over mDNS.
- Camera stream: `http://atlas-camera.local:81/stream`.
- Verified camera throughput: 23.62 FPS raw and 22.75 FPS with desktop
  rendering at 640x480, JPEG quality 10.
- Verified Orin NX YOLO median inference: 40.6 ms at image size 416.
- Post-handling preflight passed with a fresh camera frame and Shokz audio.
- Live detection recognized Tutankhamun's mask at approximately 50-90%.
- Added a short two-note Shokz listening cue immediately before Whisper starts
  recording. The standalone cue test succeeded and all 131 tests passed.
- The supplied XIAO heatsink is deliberately not installed yet because it
  blocks BAT+ and BAT-. Attach future battery leads before the heatsink.
- Neither the integrated nor old repo currently has a `.env`; Gemini is still
  mock/cloud-disabled.
- Next session: rerun one complete gaze -> cue -> question -> response cycle,
  then move to EV3/artwork motor integration when the hardware is available.

## 2026-08-02 End-To-End Runtime And Gemini Update

- Fixed Shokz playback to prefer its named PulseAudio sink and fall back to
  ALSA only when necessary. This resolved `Device or resource busy` during a
  complete ATLAS interaction.
- Tightened Shokz capture discovery so PulseAudio playback-monitor sources are
  ignored. Final preflight selected the real Loop120 mono microphone.
- Initialized RAG on the runtime's owning thread during preload, fixing a
  SQLite cross-thread exception found during the first full interaction.
- Completed a mock end-to-end cycle: camera, centered Mona Lisa hold, listening
  cue, Shokz microphone, Whisper, RAG, mock answer, Piper, and clean exit.
- Added the Gemini key privately to the integrated repo `.env` with permission
  mode 600. The key itself was never copied into this log or source control.
- With explicit cloud-test approval, completed one real Gemini cycle through
  the same hardware path. Only the transcript and retrieved artwork text were
  sent to Gemini; raw camera frames and microphone audio stayed local.
- Migrated from retired `google-generativeai` to supported `google-genai` and
  added an offline fake-client regression test. No additional cloud call was
  made after this migration.
- Final full suite: 135 passed, with one unrelated Starlette deprecation
  warning.
- Final hardware preflight with the camera opened: 0 failures. CUDA, YOLO,
  English/French Piper voices, Shokz input/output, Gemini configuration, and a
  fresh `atlas-camera.local` frame all passed. EV3 remains intentionally
  disabled until the brick and artwork mechanism are present.
- No ATLAS interaction process was intentionally left running.

## 2026-08-03 Continuous Listening And Shokz Recovery

- Confirmed from runtime logs that Deepgram started successfully and handled
  the first question, then both Deepgram and Whisper failed to reopen the raw
  Shokz ALSA input with PortAudio error `-9985`.
- Changed Shokz capture to use PortAudio's PulseAudio virtual input instead of
  the exclusive raw USB ALSA device. Live startup now reports Whisper input
  index 32; Deepgram remains the ready primary provider.
- Added automatic Deepgram recovery after a transient primary failure instead
  of leaving all later questions locked to Whisper until restart.
- Decoupled microphone capture from artwork detection. Starting a dashboard
  session now plays one cue and keeps reopening local Silero-VAD listening
  windows; artwork detection only updates response and mechanical context.
- Paused microphone capture while ATLAS generates and speaks a response so it
  cannot transcribe its own Cartesia output.
- Changed dashboard Capture Artwork so capture no longer starts a second beep
  or microphone window. A live unknown-artwork capture failed cleanly while
  Deepgram continued listening before, during, and after the request.
- Final deployment passed 90 focused tests with one Starlette deprecation
  warning. Service health passed and a rollback backup was retained at
  `/tmp/atlas_current_backup_20260803_190619.tar.gz`.
- Live idle validation passed across more than ten consecutive Deepgram/Silero
  windows with no ALSA error and no fallback. A human-spoken full
  STT-to-RAG-to-Gemini-to-Cartesia cycle remains to be tested.
