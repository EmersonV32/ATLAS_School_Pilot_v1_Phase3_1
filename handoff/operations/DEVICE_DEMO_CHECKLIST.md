# ATLAS device demo checklist

Run this in order. Stop at the first failed gate; do not hide one failure by
changing multiple systems at once.

## Before leaving for the venue

- [ ] Current commit and rollback tag are pushed to GitHub.
- [ ] Deployment command and SSH key location are known to the operator.
- [ ] Judge video, public website, and slides work without the Jetson network.
- [ ] Shokz, judge speaker, camera, Jetson PSU, display, network adapter, and
      charging cables are packed and labeled.
- [ ] Previous working YOLO `.pt` and TensorRT `.engine` remain available.

## Thirty minutes before judges

1. Boot the Jetson and wait for `atlas.service`.
2. Open `/admin`, unlock it, and use the **Main** tab for the complete check.
3. Confirm camera feed and observed FPS in **Audio / Vision**.
4. Confirm Shokz microphone input. Test Shokz output at a safe volume.
5. Switch to judge speaker, play **Test sound**, and return to the intended
   presentation route.
6. Confirm Cartesia. Temporarily exercise Piper fallback and listen for one
   consistent voice across a multi-sentence answer.
7. Run the artwork contract validator and one physical-camera pass for every
   detector class.
8. Start Demo, complete two conversation cycles, switch language verbally,
   manual-capture once, and stop manually.
9. Disconnect and reconnect the camera and Shokz. Dashboards must remain open;
   readiness must recover without restarting the website.
10. Clear simulations, temporary visitor data, manual artwork override, and
    emergency stop state.

## Five minutes before judges

- [ ] Admin **Demo** tab is open and unlocked.
- [ ] Correct language, profile, content pack, output route, and volume are set.
- [ ] Camera is cool, connected, and aimed forward.
- [ ] One operator owns the controls; one presenter owns the narration.
- [ ] Prerecorded video is paused at frame zero and locally available.
- [ ] No API keys, raw logs, home IP information, or admin token are visible.

## Pass criteria

- [ ] ATLAS stays active until **End** is pressed.
- [ ] Immediate follow-up context survives at least three visitor turns.
- [ ] Spoken language switching changes both recognition and response language.
- [ ] A five-second stable artwork prompts once, not repeatedly.
- [ ] Manual capture works from both headset and dashboard.
- [ ] Audio route and volume changes take effect without changing microphone.
- [ ] Camera disconnect never makes visitor or admin dashboard unreachable.
