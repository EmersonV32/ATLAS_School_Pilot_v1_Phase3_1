# Direct SG90 camera pan - reComputer Super J4012 / Orin NX 16 GB

Originally prepared on `codex/jetson-direct-camera-pan`, based on the latest
dashboard, readable activity, conversation and listening work. Controller and
dashboard source are now installed on the Jetson; physical motor activation
has NOT occurred. See the October 25 status below.
This supersedes the PCA9685-only proposal on `codex/arducam-sg90-pan`.
The retained PCA9685 option remains compatible; it is not required for direct PWM.

## October 25 physical preparation status

The owner has SG90 servos with three-socket plugs, but no verified power supply.
Do not plug that block onto three adjacent header pins: separate mapped jumper
connections are required. No soldering to the Jetson is needed.

Read-only discovery on the real Super / Orin NX 16 GB finds `3280000.pwm`
(physical pin 15 route) and `32e0000.pwm` (physical pin 32 route). Both report
one unexported channel and writable export/unexport under the existing user.
No output was exported, PWM generated, boot settings changed or motor moved.
Discovery does not prove header pinmux, waveform or servo compatibility.

Motor power, a suitable connector/breakout for that supply, common-ground
wiring, PWM routing/signal verification and a supervised bare-servo calibration
are still required. Send the supply's label/rating before choosing it. Do not
assume the existing Jetson barrel adapter, camera battery or a USB cable alone
is suitable. Follow the wiring and commissioning steps below; pan remains OFF.

## What is implemented

- Existing `atlas.service` / DeviceRuntime owns an optional independent pan
  controller. No second service, GPIO bit-banging, camera driver change, model
  export, voice change, or additional direct-PWM Python dependency.
- Slow automatic sweep to the configured upper limit, back to the lower limit,
  and repeat. Defaults are nominal 0-180 degrees at 5 degrees/s: 36 seconds per
  full leg. Actual travel must be calibrated; software labels do not prove 180.
- Staff **Arducam** view: private camera preview alongside hold-left/right,
  target slider, center, pause, resume sweep and all-motor safety stop. Mouse,
  touch and keyboard controls; no controls on the visitor page.
- Manual movement interrupts sweep. Release holds the last commanded position;
  automatic sweep resumes only on explicit request. Jog leases expire after
  0.6 seconds without renewal, plus scheduling delay. Release can overtake a
  pending jog request; stale sequences and pre-safety-stop packets are rejected.
- Hiding/leaving the tab, window blur, auth lock and connection loss stop jog
  renewals. An already requested sweep or target move can continue after losing
  the dashboard connection. This is stated in the UI, not misreported as stopped.
- Emergency stop removes PWM; clearing it does not resume motion. Shutdown
  releases only ATLAS's own output. Missing setup, permissions or PWM faults
  leave pan unavailable without disabling the rest of ATLAS. No auto-reconnect.
- Non-device modes always simulate; status labels say Simulation. Angles are
  open-loop commands, not measured positions. SG90 provides no feedback.

## Verified design references and important limitations

The user confirmed Seeed reComputer Super / Jetson Orin NX 16 GB (J4012).
The [Seeed Super hardware wiki](https://wiki.seeedstudio.com/recomputer_jetson_super_hardware_interfaces_usage/)
maps physical J10 pin 32 to PG.06 / GPIO07 and pin 15 to PN.01 / GPIO12.
The [Super J401 schematic, sheet 23](https://files.seeedstudio.com/products/NVIDIA-Jetson/reComputer%20Super%20J401_v1.0_SCH_PDF_250401.pdf)
visually confirms those header signal nets and the 3.3 V level shifters.
[NVIDIA's Orin NX pin data](https://github.com/NVIDIA/jetson-gpio/blob/master/lib/python/Jetson/GPIO/gpio_pin_data.py)
maps those SoC pins to hardware controllers `32e0000.pwm` and `3280000.pwm`.

Some tables in Seeed's older manual disagree with the current wiki. Do not use
generic Nano pins, physical pin 33 (listed reserved by the Super wiki), the
cooling-fan PWM, or a GPIO number copied from another carrier. Direct mode only
permits the two routes above; default is **J10 physical pin 32**. Verify the
actual carrier revision and installed pinmux before connecting a motor.

The Linux driver discovers the selected platform controller by its identity,
not an unstable `pwmchipN` number, and exports channel 0 at 50 Hz. An already
exported channel is refused, even if disabled. Same-user ATLAS processes share
a file lock; other programs that ignore it are not prevented from interfering.
Neither discovery nor successful writes prove a PWM waveform reaches J10.

**No guarantee of "only three wires" yet.** Seeed warns that the TXB0108 header
level shifters have weak drive. Direct PWM needs the actual servo's input to
accept the header's 3.3 V waveform without overloading it. A suitable buffer
may be needed if the waveform collapses; never add a strong pull-up or inject
5 V into a Jetson signal pin to compensate. Verify with an appropriate scope
or logic analyzer before enabling movement; no waveform was measured here.

## Wiring plan - ALL power disconnected

The camera remains plugged into its existing CSI connector. It mounts
mechanically on the servo horn, with cable slack and strain relief; it does
not connect electrically through the servo.

| SG90 connection (verify your unit's colors) | Direct route |
| --- | --- |
| Signal, usually orange/yellow | J10 **physical pin 32**, only after enabling/verifying PWM7 on PG.06 |
| Ground, usually brown/black | Jetson J10 **pin 6 GND** and servo-supply negative, common ground |
| Positive, usually red | A verified servo-rated supply, not a GPIO or 3.3 V pin |

Pin numbers are physical positions, **not BCM/GPIO numbering**. Identify J10
and its pin-1 marking from the exact carrier; do not count from an assumed
orientation. No soldering to the Jetson or CSI connector is needed.

[TowerPro's genuine positional SG90 specification](https://towerpro.com.tw/product/sg90-analog/)
states 4.8 V and external-adapter power. Verify the actual unit's allowed range
before using a regulated 5 V supply. Size its supply and wiring for startup and
stall current under the camera load, not idle current. Do not use a continuous
rotation/360-degree servo for angle control.

The [Seeed Super manual, pages 34-37](https://files.seeedstudio.com/products/NVIDIA-Jetson/reComputer_super_user_manual.pdf)
lists J10 pins 2/4 as 5 V and a 1 A continuous capability. Jetson-header power is
an option **only after** verifying the servo voltage, available shared power
budget, transient load, wiring and stability with ATLAS running. This is not
certification that it will work with the user's servo. A regulated external
supply/common ground is the reliability recommendation. If using external
power, leave its positive disconnected from Jetson pins 2/4: no backfeeding.
Never use the Jetson's 12-19 V input, fan power, exhibit servo rail, GPIO output,
3.3 V supply or camera battery pads for the SG90. Provide a physical motor-power
disconnect; software stop is not a safety-rated power cutoff and does not
guarantee zero torque in every servo failure.

## Setup - no automatic system modifications

Before a future approved deployment, keep servo power disconnected:

1. Confirm the exact carrier/connector and installed JetPack/L4T image. Back up
   reviewed source and boot configuration. Do not upgrade/flash the recovered
   Jetson, change package holds, or download a generic overlay for this feature.
2. Inspect the existing Jetson-IO tool for PWM7 on physical pin 32. A separate,
   approved pinmux setup/reboot may be needed. If that route is unavailable on
   the installed image, stop and investigate; do not write raw hardware registers
   or silently select a cooling-fan output. Pin 15/PWM1 is a supported alternative
   only with verified routing, wiring and `jetson_board_pin: 15`.
3. Run read-only discovery with the **existing service's Python and user**:

   ```bash
   /path/to/existing/venv/bin/python scripts/check_camera_pan_pwm.py
   ```

   It does not load `.env`, export PWM, move the motor or access the camera.
   Missing controller, already exported channel or unwritable export/unexport
   needs inspection. It does not set permissions. Verify access to the eventual
   `pwm0` attributes via narrowly scoped local permissions/udev rules; do not
   run the whole AI service as root or make `/sys` globally writable.
4. Verify signal frequency, polarity, amplitude and pulse widths on the selected
   output and the servo input. Confirm suitable motor power. A PWM permission
   check is not electrical acceptance.
5. Test/calibrate the **bare servo first**, with a reduced safe arc and camera
   removed, ideally using a servo tester. Pulse placeholders 1000/2000 us do not
   prove a safe or complete 180-degree arc. Never blindly apply 500/2500 us,
   force mechanical stops, or tension the CSI ribbon. Mount only after safe
   travel/neutral/load and cable slack have been verified.

Merge only this optional section into the actual existing device config;
do not replace credentials, Wi-Fi, audio, model or service configuration:

```yaml
camera_pan:
  enabled: false
  driver: jetson_pwm
  jetson_board_pin: 32
  pinmux_confirmed: false
  power_confirmed: false
  calibration_confirmed: false
  startup_mode: hold      # first supervised start; later sweep
  min_angle: 0            # REPLACE travel/pulses with verified safe calibration
  max_angle: 180
  center_angle: 90
  min_pulse_us: 1000
  max_pulse_us: 2000
  sweep_speed_deg_s: 5
  manual_speed_deg_s: 15
```

Only set the three confirmations and `enabled: true` after their checks pass.
`startup_mode: hold` still immediately commands center when the driver opens,
which can cause a jump from an unknown physical starting position. Keep the
bare servo/mount clear. After supervised acceptance choose `startup_mode: sweep`
for normal automatic operation. The dashboard cannot enable an uncalibrated
motor or change PWM wiring/pulse endpoints. Missing `camera_pan` remains off;
old PCA9685 configs retain the previous backend default. PCA9685 requires the
optional `camera-pan` dependency, explicit I2C bus, dedicated board and its own
verified wiring, not this direct wiring plan.

## Physical commissioning and acceptance still required

The following source-deployment procedure was written before the combined
software was installed. The current status above takes precedence; physical
commissioning remains pending. No motor configuration or boot file was changed
on October 25. Use the reviewed **combined feature branch**, not
the earlier PCA-only patch/bundle. Compare the actual installed source first,
then apply only approved source/config changes with a reversible backup and
run the existing isolated regression wrapper. Keep pan disabled on first
deployment. Start/restart the existing `atlas.service` only when approved.

Supervised acceptance must cover sweep/reversal, safe arc/mount/cable strain,
both jog directions/release, center/target speed, tab switch, touch cancel,
keyboard release, disconnect/late packet, stop/clear/explicit resume, shutdown
and service restart, waveform and power stability, and live Arducam preview.
Also test camera, YOLO, headset mic, complete spoken answers, pauses and
same/new-artwork context while the motor runs under load. Laptop mocks cannot
certify mechanical safety, power stability, PWM routing, real speech or hardware.

## Local regression verification

Synthetic tests cover waveform conversion/50 Hz configuration, controller
identity, no fan/shared output changes, ownership/export/permission failures,
invalid pulses/settings, calibration/setup gates, slow sweep and reversals,
manual override, expired jog, stale commands, emergency-stop epochs, lifecycle
and fault isolation. Dashboard tests use intercepted mock APIs, never hardware
or provider keys. Final local gate: **3,323 passed, one expected skip**, with
the existing non-failing Starlette/httpx deprecation warning. Synthetic
JavaScript checks: 81. Headless browser: 35 layouts, 29 control requests, 10
failure/recovery checks, 2,717 contrast checks, no unexpected browser errors.
Ruff, compile, dependency, secret, recovery and whitespace checks passed.
Visitor onboarding again passed 33 keyboard transitions at 1024x768 with
reduced motion, no browser errors and no visitor browser storage/cookies.
These are software-only results, not physical acceptance.
