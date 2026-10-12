# SG90 camera pan: resume next hardware session

Recorded 2026-10-11. The user asked to defer this work because the hardware is
not currently with them, and to preserve today's discussion for continuation.
This note is not approval to deploy, change device configuration, or wire live
hardware. Resume only when the user returns to this task.

## Intended feature

- Mount the Arducam on a standard positional TowerPro-style SG90 9 g servo.
- Slowly sweep through the physically verified safe arc, nominally 180 degrees,
  then return and repeat under the existing `atlas.service`.
- Override left/right from the staff dashboard while watching the Arducam
  preview; support pause, center, resume, and emergency stop.
- Human-following is a possible later feature, not part of this first stage.
- Preserve voice continuity, conversational context, YOLO, camera streaming,
  visitor privacy, and the existing service configuration.

## What the user has reported

- A photo of an SG90-style servo kit with three-wire lead, horns, and screws.
  A controller board was not shown; authenticity, voltage rating, positional
  versus continuous rotation, and true travel are not confirmed by that photo.
- Female-to-female, male-to-female, and male-to-male jumper wires.
- They can solder if necessary, but avoid requiring soldering without a need.
- No suitable separate servo power supply or PCA9685 board has been confirmed.
- The user prefers investigating whether only the servo and existing jumper
  wires can be used with direct Jetson control and Jetson-supplied power.
  This is an option to investigate, not an accepted or verified wiring design.
- The last reported state was that the Jetson, camera, and headset were offline.
  Confirm their actual state when resuming.

## Software already prepared, not deployed

- Feature branch: `codex/arducam-sg90-pan`; `main` remains the maintained branch.
- Current driver supports a dedicated PCA9685 board, not direct Jetson PWM.
- Optional pan is disabled until configuration and calibration are confirmed.
- Laptop validation recorded 3,133 passing tests, one expected skip, and the
  existing non-failing deprecation warning, plus simulated dashboard controls.
  None of this proves physical servo operation or power stability.
- See [the implementation/deployment guide](../atlas/docs/CAMERA_PAN.md).
- A feature-only offline deployment bundle was prepared in the owner's local
  `ATLAS/deployment-packages/` directory. It is not a GitHub dependency and does
  not yet support the proposed direct-PWM route. Rebuild/revalidate any bundle
  if the driver or deployment instructions change.

## Important clarification about power

The earlier recommendation of a separate power supply was for reliability,
not proof that Jetson power is always unusable. The Seeed reComputer Super J401
manual documents a 5 V expansion-header supply with 1 A continuous capacity.
That does not establish available startup/stall current or noise immunity with
the actual ATLAS load. TowerPro's official positional SG90 listing specifies
4.8 V; verify the actual unit's allowed voltage before using a 5 V supply.

Direct operation with just the servo and jumper wires remains conditional on
power, control-signal compatibility, and physical testing. Never power the
servo from a GPIO signal output, the 3.3 V logic rail, or camera battery pads.
Do not backfeed the Jetson or use the exhibit's higher-voltage servo rail.

## Checks and work for the next session

1. Confirm the actual Jetson carrier/revision, servo product specification,
   existing power adapter/load, accessible connections, and mount/cable slack.
   Repository records identify a Seeed reComputer Super J401 / Orin NX 16 GB;
   do not substitute generic Jetson Nano pin instructions.
2. Investigate direct hardware PWM on the actual carrier and installed image.
   Verify pin routing, pinmux, permissions, signal voltage and drive strength.
   The Seeed manual warns that the header's level-shifted GPIO has weak drive;
   extra interface hardware may be needed. Do not promise wires alone.
3. Verify servo startup/stall demand and available 5 V capacity. Choose Jetson
   power only if the actual unit and system permit it and tests are stable;
   otherwise use a correctly rated regulated external supply/common ground.
4. If the direct route is viable and requested, add/test an optional direct-PWM
   driver while retaining the existing disabled/mock behavior and bounded
   controller, dashboard priority, disconnect handling, and safety limits.
   Do not implement software-timed GPIO pulses alongside ATLAS inference/audio.
5. Calibrate the bare servo conservatively before mounting the camera; avoid
   hard stops, cable tension, and assuming a true 180-degree physical arc.
6. Run software regressions, including voice/context. Deploy only with explicit
   approval and rollback, using the existing service and environment without
   JetPack/L4T upgrades or unrelated model/firmware changes.
7. Supervise physical acceptance: sweep/reversal, manual override/release,
   network disconnect, emergency stop/clear, shutdown/restart, preview, power
   stability, and normal speech with follow-up context under load.

## Verified reference documents (not physical acceptance)

- [Seeed reComputer Super manual, expansion header pages 34-37](https://files.seeedstudio.com/products/NVIDIA-Jetson/reComputer_super_user_manual.pdf)
- [NVIDIA Jetson.GPIO: hardware PWM and separate pinmux configuration](https://github.com/NVIDIA/jetson-gpio#11-pwm)
- [TowerPro positional SG90 specifications](https://towerpro.com.tw/product/sg90-analog/)
- [Adafruit servo power: motor current and shared-supply brownout risks](https://learn.adafruit.com/16-channel-pwm-servo-driver/hooking-it-up)
