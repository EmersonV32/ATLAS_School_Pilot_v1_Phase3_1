# SG90 Arducam pan: deployment and physical acceptance

Software feature: `codex/arducam-sg90-pan`. No physical device was contacted.
This version supports a **dedicated PCA9685 controller**, not arbitrary direct
Jetson GPIO. The wiring decision is still pending. `atlas.service` already runs
DeviceRuntime, which now owns the optional pan controller; no second service,
firmware flash, YOLO export, or voice/context change is required.

## What it does

- When explicitly enabled and calibrated in device mode: command the center,
  sweep to the upper limit, back to the lower limit, and repeat at 5 degrees/s.
  A nominal 180-degree leg takes 36 seconds. Change limits for the actual mount.
- Staff dashboard **Arducam** tab: private live preview, hold-left/right (mouse,
  touch, or focused Enter/Space), center, target slider, pause, resume sweep,
  and emergency stop. Visitor pages have no movement controls.
- Manual commands interrupt the sweep. Releasing a held button leaves the
  camera holding its commanded position. Resume automatic sweep explicitly.
- Jog renewals expire after 0.6 seconds, plus at most one 0.05-second motion
  tick under normal scheduling. Tab changes, blur, hiding, and network failures
  stop renewals. Delayed command sequences are rejected. A safety-stop/reset
  epoch prevents old packets from rearming movement after clearing the stop.
- Global emergency stop disables this channel and stops the separate exhibit.
  Clearing it **does not resume movement**. Shutdown disables this channel;
  no surprise return-to-center move is sent.
- Missing board, missing optional library, invalid configuration, or a bus
  fault leaves pan unavailable without changing speech or dialogue. Faults
  require inspection/restart; there is no automatic hardware reconnect/move.
- Dev/demo modes always simulate movement, even when enabled. Their dashboard
  explicitly says **Simulation**. No I2C module is imported in these modes.

Angles are **commanded estimates**, not measured positions: SG90 has no position
feedback. Endpoint accuracy, speed, mounting strength, stall current, and
actual physical travel cannot be certified by laptop tests.

## Hardware choice and wiring (power disconnected)

Use a standard **positional** SG90, not an SG90 continuous-rotation/360 model.
The manufacturer's positional SG90 specifies 4.8 V operation and an external
power supply; verify the exact genuine servo and supply before connecting it.
Do not use the exhibit FeeTech servo's higher-voltage rail.

Recommended wiring, after identifying the reComputer's actual header/bus:

| Connection | Destination |
| --- | --- |
| Jetson 3.3 V logic | PCA9685 VCC, not V+ |
| Verified header SDA / SCL | PCA9685 SDA / SCL |
| Jetson GND | PCA9685 GND and servo-supply GND (common reference) |
| Separate regulated, servo-rated supply | PCA9685 V+ / servo positive |
| SG90 signal (verify wire colors) | Configured PCA9685 channel PWM/S |
| SG90 power / ground | Channel V+ / GND |

Never power the servo from a GPIO signal pin or the 3.3 V logic rail. Use a
supply sized for motor startup/stall load, with an accessible physical power
disconnect. Follow the module vendor's supply/decoupling instructions. Avoid
backfeeding Jetson power. Wire colors and board pin order must be verified.

PCA9685 frequency is shared across all 16 channels. Reserve this board for the
camera only: this implementation refuses other active channels and an external
clock, never broadcasts a reset, and only disables its own channel. A Linux
file lock prevents another ATLAS process under the same user owning this board.
It cannot exclude another program/user that ignores this lock.

No Jetson header pin/bus is guessed. Inspect the exact carrier's documentation
and existing `/dev/i2c-*` interfaces without changing JetPack/L4T or package
holds. Direct Jetson GPIO is **not implemented here**; NVIDIA's GPIO library
requires a real hardware-PWM pin with separately configured pinmux.

## Configuration and calibration

Older installation configs remain compatible: missing `camera_pan` defaults
to disabled. Configuration must be explicit; the dashboard cannot enable an
uncalibrated motor or edit pulse endpoints.

Add/merge this section into the device's existing `config/settings.yaml`;
do not replace Wi-Fi, audio, models, dashboard authentication, or other settings:

```yaml
camera_pan:
  enabled: false
  calibration_confirmed: false
  i2c_bus: null        # replace with the verified carrier/header bus number
  i2c_address: 0x40    # verify board address jumpers
  channel: 0          # verify the dedicated camera signal channel
  min_angle: 0
  max_angle: 180
  center_angle: 90
  min_pulse_us: 1000  # placeholders; not proof of 180-degree physical travel
  max_pulse_us: 2000
  sweep_speed_deg_s: 5
  manual_speed_deg_s: 15
```

1. Stop ATLAS and disconnect motor power. Verify hardware and mount load. First
   center/test the bare servo using a suitable servo tester and the exact servo
   documentation; do not attach the camera until neutral and travel are known.
2. Determine conservative safe pulse endpoints with a servo tester. Never
   blindly send 500/2500 us or force a hard stop. The software permits those
   bounds only so a verified servo can be calibrated. It does not prove they
   are safe for your unit.
3. Fit the camera with slack/strain relief in the CSI cable. Check the complete
   arc for collisions and cable tension while powered off. Reduce travel if
   necessary. An SG90/camera mount may not support a true 180-degree sweep.
4. Enter the verified bus, channel, travel labels, pulse endpoints, and center.
   Only after this physical verification set `calibration_confirmed: true` and
   `enabled: true`. Startup sends the configured center immediately; a servo
   already elsewhere can move abruptly to center. Keep people/cables clear.
5. First live start must be supervised, preferably with a reduced verified
   arc. Expand to the full verified arc only after the acceptance checks below.

The service starts automatic sweep only after its normal critical runtime
components preload. The movement worker sleeps between 20 Hz updates; PCA9685
generates the 50 Hz signal in hardware. No camera frames or visitor information
are stored by this feature.

## Feature-only deployment, once explicitly approved

Use the accompanying **camera-pan-runtime.patch**, based on main `9dfe260`.
It includes only affected source files, the optional dependency declaration,
and the new regression tests. It deliberately excludes device configuration,
service units, YOLO weights/engines, firmware, and private files. Do not use the
older all-in-one visitor/model uploader for a servo-only deployment.

On the Jetson, in the *actual installed application's* directory (containing
`src/atlas`, `config`, and `pyproject.toml`), after transferring the patch:

```bash
# First cut servo power. Use the existing service's actual user/root.
systemctl --user stop atlas.service
git apply --check /path/to/camera-pan-runtime.patch
git apply /path/to/camera-pan-runtime.patch
# Use the exact existing atlas.service virtual-environment Python:
/path/to/existing/venv/bin/python scripts/run_deployment_pytest.py
```

If `git apply --check` fails, stop: the installed source differs from the
reviewed baseline. Do not force it or overwrite unrelated changes. Keep the
patch unchanged for reversible rollback. Existing runtime configuration is
preserved; keep pan disabled through deployment and the initial service check.

When wiring is decided, install **only** the small optional I2C library into
that same existing virtual environment, with explicit approval:

```bash
/path/to/existing/venv/bin/python -m pip install --no-deps 'smbus2>=0.4,<1'
```

For offline installation, obtain the compatible smbus2 wheel beforehand and
use `--no-index --no-deps /path/to/wheel`. Do not reinstall ATLAS's heavy
dependencies, upgrade JetPack/L4T, replace the service, or rebuild TensorRT.
Read/confirm the existing service's working directory and Python executable
before substituting paths. Tests do not load the installed `.env`.

With pan still disabled, restart the existing service and confirm ordinary
voice/context, visitor dashboard, and Arducam preview. Then perform the
calibration/activation process above and restart under supervision.

Rollback (with servo power disconnected and service stopped):

```bash
git apply -R --check /path/to/camera-pan-runtime.patch
git apply -R /path/to/camera-pan-runtime.patch
```

Remove the newly added `camera_pan` config section before restarting old code,
because old settings reject unknown fields. If reverse checking fails, inspect
intervening edits; do not overwrite them. The original model/audio/firmware
files and service unit are never touched by the feature patch.

## Acceptance gate: still due on physical hardware

- Verify standard positional SG90, dedicated board, supply, common ground,
  carrier bus/channel mapping, and safe CSI cable clearance.
- With mount clear: center, slow back-and-forth repeat, left/right direction,
  endpoint reversal, slider limits, pause, manual release, explicit resume.
  Swap physical orientation if left/right is reversed; do not extend pulses.
- While viewing live preview: keyboard and touch override. Disconnect the
  dashboard network while holding jog; confirm movement stops and stays held.
- Test global emergency stop, clear-without-resume, service stop/restart, and
  missing/unplugged controller. Check pan faults do not break voice/context.
- Run normal conversations while sweeping and operating the preview; verify
  speech is continuous and follow-up context survives. Check supply stability,
  mount load, temperatures, audible buzzing/stall, and real PWM pulse widths.
- Test actual iPad Safari; desktop reduced-motion/keyboard QA is not proof of
  physical touch behavior or servo movement.

A software emergency stop is **not a certified hardware safety circuit**.
PCA9685 can retain PWM when the process crashes or I2C fails. Disabling pulses
does not cut motor power and may release holding torque. Use the physical
servo-supply disconnect if motion continues or a stop cannot be confirmed.
The software stop latch is process-local: a service restart starts a new
controller and, when enabled/calibrated, starts its sweep again. Disconnect
motor power during recovery or maintenance rather than relying on this latch.

## Future following feature

Human detection/tracking is intentionally absent. A later local tracking
module should issue bounded targets through `CameraPanController`, never raw
PWM, and explicitly implement manual/safety priority and target-loss behavior.
This feature adds no face recognition or identifying visitor storage.

## Hardware references

- [TowerPro positional SG90](https://towerpro.com.tw/product/sg90-analog/)
- [PCA9685 module pinout and separate motor supply](https://learn.adafruit.com/16-channel-pwm-servo-driver/pinouts)
- [NXP PCA9685 datasheet: common frequency and register sequencing](https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf)
- [NVIDIA Jetson.GPIO hardware-PWM limitations](https://github.com/NVIDIA/jetson-gpio)
