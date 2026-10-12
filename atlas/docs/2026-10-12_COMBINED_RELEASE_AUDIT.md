# Combined release audit — October 12, 2026

## Release decision

The local candidate is `codex/combined-release-audit`, based on `fcfbd02` on
`codex/jetson-direct-camera-pan`. It includes the October 11 conversation and
listening work and October 12 dashboard, readable activity and direct SG90 pan
work. `main` remains the maintained baseline at `9dfe260`.
Implementation/regression commit: `da8dbca` (local, not pushed or deployed).

This is a software release candidate, **not a completed deployment or a
flawless, physically verified installation**. No push, merge to `main`, Jetson
connection, firmware flash, package installation, live configuration or service
change occurred in this audit. Jetson, cameras, headset and servo were offline.
Pan remains disabled by default. Mechanical work remains deferred.

The existing XIAO stream-watchdog timing defect below remains open. Fixing it
requires a separate firmware task; repository safety instructions forbid
firmware changes during dashboard work. Do not certify the complete camera
workflow until that defect and the live acceptance gates have been addressed.

Use this combined candidate, not the earlier PCA-only branch or an old release
bundle. The application package remains `0.1.0`. The seven-class YOLO26 Nano v6
checkpoint is unchanged, SHA-256
`af11b2de376a5c54a1ee11e9765f91ecbf54a1f308a2a82f9106b00a78409731`.

## Gaps reproduced and corrected

| Gap | Correction and regression coverage |
| --- | --- |
| Typed current-view questions could use an old remembered artwork after detection/frame loss. | Additive `live_artwork_id` / `current_view_confirmed` status distinguishes discussion memory from confirmed selection. Typed questions use that live focus. Tests cover lost detection, stalled camera, retained ordinary follow-ups and a new artwork. |
| A stopped camera reader still returned its last frame to previews/capture. | Frames older than 4.5 seconds are unavailable rather than repeatedly served as live. Tests cover stale-copy rejection and fresh-frame recovery. |
| A streaming sentence rejection/exception could be reported as successful speech if the final drain succeeded. | Both pipeline entry points retain each segment result; a lost segment makes the overall speech result fail without replaying the answer. Four regressions cover rejection/exception in both paths. |
| An activity-log write failure could discard a successfully generated typed answer. | Logging failure no longer discards the answer or its visit memory. A synthetic disk-write failure verifies the result is retained. |
| Late protected status/images from an earlier dashboard unlock could affect a newly unlocked view. | Access-generation/token checks discard old responses and decoded frames. A new access gets a fresh preview. Synthetic JavaScript tests cover same-token re-unlock, token change and both previews. |
| Stopping a visit could wait for whole-answer Cartesia speech, or retry the cancelled answer through fallback. Local Piper playback was not cancellable. | Independent cancellation generations interrupt the owned socket/player/processes without waiting on the speech lock. Cancelled speech cannot retry the old answer through fallback. Six synthetic regressions cover socket wait, before/after first audio, late connection/player creation, fallback suppression and local playback. |
| The new hesitation/question-length settings were invisible in the dashboard, making old overrides hard to spot. | Protected settings now expose and validate both limits. Labels distinguish initial waiting from question length. API and browser tests verify visibility, bounds, saved values and the restart-required indication. |
| Local Piper playback killed valid answers longer than 30 seconds. | Playback now uses the generated WAV duration plus a 10-second margin (minimum 30 seconds), while synthesis keeps its separate finite deadline. A virtual 60-second-answer regression verifies completion without real audio or sleeping. Cancellation remains available during playback. |

The earlier context/listening fixes are retained: shared typed/spoken visit
memory, explicit artwork transitions, multi-artwork retrieval, accent/filler
guidance, Deepgram segment merging, unfinished-question grace, cancellation
and delayed-capture invalidation. See the
[workflow record](2026-10-11_CONVERSATION_LISTENING_STABILITY.md).

Production still uses complete-answer speech with one selected provider per
answer; `Container` deliberately sets `stream_responses=False`. Streaming
adapter regression coverage is not a claim that streaming has been enabled.
Before-audio provider failure can use a complete fallback answer. Once audio
has started, a failure must not replay that answer in another voice. Physical
playback and provider failures still need the tests below.

## Software verification

Final complete release gate: **3,345 passed, one expected skip, one existing
non-failing deprecation warning**, in 316.70 seconds. The skip is the opt-in
real YOLO inference test requiring the separate CPU ML environment; this audit
did not install that environment or change the checkpoint. The warning concerns
Starlette's TestClient/httpx integration, not a runtime failure.

Focused source/workflow/pipeline regressions passed 92 tests; final voice
adapter/cancellation/long-answer regressions passed 31 tests. Ruff, compilation,
dependency consistency, secret scan, recovery bundle, repository navigation
and staged/unstaged whitespace checks all passed. No production dependency was
added or updated in this audit.

Tests run through `scripts/run_deployment_pytest.py`, which blocks discovery
of the real installation's dotenv files. Sockets, devices, processes, audio,
cloud providers and dashboard responses in regressions are synthetic.

Headless Chrome used the real dashboard HTML/CSS/JavaScript with every request
intercepted: **35 layouts, 30 control checks, 10 failure/recovery scenarios,
2,725 contrast checks, no unexpected browser errors**. The rendered overview,
readable activity and direct-pan view were also inspected. JavaScript logic:
**97 checks passed**. Visitor browser regression: **33 keyboard transitions
at 1024×768**, reduced motion, six locales, no page errors, bad responses or
visitor cookies/local/session storage. Sites skill guidance informed the local
responsive/accessibility verification; no hosted site or frontend dependency
was introduced.

Generated browser screenshots/reports are outside Git under
`ATLAS/repository-backups/2026-10-12-combined-audit-qa/`; they use public artwork
and synthetic text only. These checks do not certify a real microphone, speaker,
camera, school network, cloud account, GPU or motor.

## Known camera firmware issue — not fixed in this audit

`firmware/xiao_camera/app_httpd.cpp:cameraStreamStalled()` subtracts the shared
`lastStreamFrameAtMs` from a previously sampled `nowMs` using unsigned
arithmetic. The stream task can update that timestamp between the caller's
time sample and the subtraction. For example, `100 - 101` wraps to a huge
elapsed value and falsely satisfies the timeout. `volatile` does not make
the pair an atomic snapshot. The caller in `xiao_camera.ino` restarts the ESP32
when the watchdog reports a stall.

This existing source defect is consistent with, but does not prove the cause
of, the operator's earlier stream-stall/reboot reports. Jetson freshness checks
protect downstream decisions from frozen frames; they do not repair this
firmware race. The separately approved firmware fix must include deterministic
future-timestamp/concurrent-update and genuine `millis()` wrap regressions,
ESP32 core build verification, reviewed flashing and an actual stream soak.
Do not simply remove all genuine stall recovery.

## Deployment preflight — when the owner brings devices online

1. Obtain explicit deployment/restart approval. Record the actual target source
   revision, service state and interpreter; do not assume the October 4 state
   or old DHCP addresses are current. Last recorded root:
   `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`; last recorded venv:
   `/home/super-alex/atlas/venvs/atlas-school-pilot/bin/python`. Retain the
   installed user `atlas.service`, service user and working directory.
2. Compare the candidate with the actual installed source and take a recoverable
   backup of the exact approved targets. Preserve private state locally without
   printing, uploading or committing it. Record whether the service was active
   or stopped so rollback restores the intended state.
3. Deploy only reviewed source/assets and necessary non-secret setting changes.
   Preserve `.env`, Wi-Fi credentials, audio routes, content/index/session state,
   camera calibration, model/engine files, installed unit and JetPack/L4T package
   holds. No generic `apt upgrade`, firmware flash, TensorRT rebuild or boot
   pinmux change belongs to this workflow/dashboard update.
4. Do not blindly run the old October 4 uploader as a workflow-only patch: it
   also packages firmware and rebuilds the model engine. Prepare a narrowly
   scoped source update against the actual installation instead. Direct pan
   uses the standard library; its presence does not require installing the
   optional PCA9685 dependency.
5. Keep `camera_pan.enabled=false` and all hardware confirmations false for the
   first release. Retain the approved v6 checkpoint and matching 416 FP16 engine.
   Compare hashes without exposing private files or changing models.
6. Review the protected, non-secret `/admin/config` or Settings page. Existing
   YAML/dashboard overrides can mask new defaults. Intended Deepgram defaults:
   wait for first speech 8 seconds; question limit 45 seconds; normal pause
   2,000 ms; unfinished-question pause 4,000 ms. Provider choices and explicit
   cloud switches must match the owner's approved installation, not laptop mocks.
   A restart-required badge means saved settings are pending, not proof they
   are active. After an approved restart, reload and confirm the badge clears
   and the intended values are active.
7. Run the isolated software gate in the target's existing environment before
   approving a restart. No key/billing readout, `.env` dump or visitor log export
   is needed. Readiness alone is not physical acceptance. If validation fails,
   do not launch a partially updated source tree; use the reviewed rollback.

## Physical and cloud acceptance checklist

All boxes below remain **pending**, not passed. Record date, candidate commit,
non-identifying test IDs, expected/observed outcome, relevant durations and
pass/fail. Do not collect raw visitor media, private profiles, names, exact ages,
credentials or prompts as evidence. Use an owner-controlled synthetic test visit.
Failed checks block the relevant feature; repair and rerun before marking it ready.

### A. Installed runtime and readiness

- [ ] Verify actual hostname/address, SSH access, source/interpreter/unit paths,
      revision and pre-update service state. Recheck after restart and cold boot.
- [ ] Confirm one runtime owns the camera/audio/controller, with no competing
      old process. Verify readiness reflects the actual connected devices.
- [ ] Confirm active non-secret speech settings, cloud opt-ins, model binding,
      content pack and fresh retrieval index. Check provider account/model access
      with a small approved request, without viewing or sharing API keys.
- [ ] Verify rollback restores the approved code and service state while retaining
      models, installed unit, private configuration and device calibration.

### B. Voice continuity, cancellation and headset

- [ ] English and Traditional Chinese spoken round trips, then each intended
      demonstration language. Check local Piper voices are installed for the
      configured offline languages; extra cloud languages need real acceptance.
- [ ] Play a long multi-sentence answer to completion on headset, speaker and
      both outputs; check beginning/end, same voice, no sentence restart, clipped
      words or audio-device mismatch. Check cue and volume independently.
- [ ] Cause an approved provider failure before first audio: at most one complete
      fallback answer. Cause a failure after first audio: no second-voice replay;
      answer text stays available and speech failure is reported honestly.
- [ ] Stop/reset a visit during listening preparation/cue, capture, Gemini/RAG
      generation, Cartesia receive/drain and local Piper playback. Old audio,
      answer, artwork or memory must not appear in the next visit; the next
      question must still work. Repeat rapid stop/start several times.
- [ ] Disconnect/reconnect the headset, change the selected route and recover
      from unavailable output. The issue board/readiness must recover accurately.
- [ ] Test the physical multifunction button: one fresh capture per press,
      no duplicate recognition and no delayed pre-reset capture restoring memory.

### C. Hesitation and imperfect speech

- [ ] A normal ~1.5-second pause followed by more speech stays in one question.
- [ ] A clearly unfinished phrase followed by a ~3-second pause and resumed
      speech stays in one question with the default 4-second grace.
- [ ] Speech beginning late in the 8-second initial wait is not cut off by that
      original deadline. A 15–30-second question is retained; the configured
      45-second utterance limit still ends a runaway capture.
- [ ] Timed final segments plus an unfinished interim tail retain the whole
      question; repeated words in separate segments are not removed.
- [ ] Try fillers, self-correction, French/English accents and artwork-name
      pronunciation differences. Clear mistakes should be understood; important
      ambiguity must prompt clarification rather than an invented artwork.
- [ ] Verify listening resumes after speech finishes, with no self-echo questions.
      This is not full-duplex barge-in. Test offline Whisper separately: it
      remains a bounded fixed-window fallback, not the adaptive Deepgram capture.

### D. Conversation, camera subjects and retrieval

- [ ] Artwork A → several pronoun/follow-up questions → artwork B: subsequent
      answers and retrieval use B, not stale A. Repeat with all seven v6 classes.
- [ ] While B remains in view, explicitly ask about A, then ask a pronoun
      follow-up: retain discussion A without falsely saying the camera sees A.
- [ ] Ask what is currently in view: use fresh B. Return the camera to A and
      verify the transition and useful earlier discussion context.
- [ ] Compare two artworks and ask a compound question. Evidence must cover
      both works, not a single canned answer with the second request dropped.
- [ ] Interleave typed and spoken questions in one visit; they share context.
      Force explicit staff selection/button capture and confirm re-selection.
- [ ] Lose detections or unplug/stall the camera: ordinary discussion remains,
      but a current-view question must not identify the old frame as fresh.
- [ ] Start a genuinely new visit: previous visitor context/profile is cleared.
      Delayed cloud answers/captures cannot restore the old visit.
- [ ] Test more than 12 exchanges and several artwork switches. Confirm useful
      earlier subject recall while respecting the memory bounds below.

### E. Cameras and networks

- [ ] Resolve the XIAO watchdog defect in a separately approved firmware task,
      then build/flash/test actual streaming, stalls, reconnects and time wrap.
- [ ] Check current XIAO control and stream endpoints, real frame timestamps,
      battery/power stability and fresh recovery after reset. A responding
      settings page is not proof of a working live stream.
- [ ] Check CSI/Argus Arducam start/stop/retry/unplug/recovery independently.
      Both previews must show current frames and visible failures, not frozen
      last images marked live.
- [ ] Test actual YOLO v6 detection/false alarms, latency, confidence and FPS
      on camera images. GPU/TensorRT/thermal acceptance remains due even though
      the checkpoint and software mapping were not changed.
- [ ] At school, verify actual enterprise authentication, server identity and
      client isolation with the network administrator. PEAP/MSCHAPv2 without
      server verification is still an unverified security assumption.
- [ ] Test school unavailable/failed → hotspot fallback on both devices and
      actual camera-to-Jetson traffic. They select independently and can land on
      different networks; neither preempts a working hotspot just because school
      appears. Validate the phone hotspot band, routing and phone-terminal SSH.

### F. Dashboard, activity and visitor experience

- [ ] Real laptop/tablet/phone LAN browsers: every navigation view, button,
      slider, setting and keyboard/touch action. Check judge-screen readability,
      1024×768 landscape, small screens and reduced-motion behavior.
- [ ] Wrong/expired token, lock/unlock during delayed status/image responses,
      lost network and reconnect: no old protected preview/data resurfaces;
      fresh previews restart and protected routes stay protected.
- [ ] Inject camera/audio/AI/pan/service failures and recovery; persistent issues
      identify the failing part and clear only after recovery. No mock readiness
      label should be confused with real device/cloud health.
- [ ] Readable activity and raw entries share snapshot/entry IDs, filters,
      pause/manual refresh and export. Check camera/button/STT/answer ordering
      on the actual runtime, respecting each source's timestamp limitations.
- [ ] Quoted question/interim/answer privacy flags off must hide those texts,
      including existing history. Turning on a view must not silently enable
      recording. Generated answer text is not proof it was played aloud.
- [ ] Simulate an isolated activity-log write failure: generated answers remain
      usable; the storage fault is visible through the operational diagnostics.
- [ ] Visitor onboarding in all six locales, wake/reset/help/emergency/transfer,
      readiness and reconnects on the real kiosk. Visitor routes must not expose
      staff previews, providers, transcripts or private profiles.
- [ ] Optional greeting name stays ephemeral and local Piper-only; no name or
      exact age is stored, logged, included in prompts or sent to cloud providers.

### G. Deferred SG90 acceptance — do not enable yet

Use [the pan setup and safety guide](CAMERA_PAN.md). Human tracking is not
implemented. Dashboard angles are commands, not measured positions.

- [ ] Verify the actual J4012 hardware PWM route/controller, permitted sysfs
      access and waveform before attaching signal. Do not use GPIO bit-banging
      or change fan/shared PWM outputs. Pinmux setup is a separate approved step.
- [ ] Verify suitable motor voltage/current under startup and stall load, common
      ground, signal compatibility and no backfeed. Do not assume the Jetson
      header is a proven safe servo power supply; never use a 3.3 V GPIO as power.
- [ ] Calibrate the bare servo using a small safe arc, then verified endpoints,
      neutral and pulses. Do not assume every SG90 can safely travel 180 degrees.
      Startup hold still commands center and can jump; keep the mechanism clear.
- [ ] Mount the camera only after calibration. Check load, stable mounting,
      ribbon/cable slack and strain throughout the verified arc.
- [ ] Sweep slowly both ways; both jog directions; touch/keyboard release;
      pointer cancellation, blur/tab/page changes, lost renewals and late packets.
      Jog should expire after its 0.6-second lease. Explicit sweep/target can
      continue after network loss: prove the operator understands that distinction.
- [ ] Pause/center/target, emergency stop, clear and explicit resume; fault
      isolation, shutdown, restart and physical power cutoff. Software stop is
      not a safety-rated cutoff or a guarantee that a gravity-loaded mount holds.
- [ ] Camera/YOLO, mic, long spoken answers, context and dashboard remain usable
      while the mounted servo is moving under actual load.

### H. Combined soak and recovery

- [ ] Run a controlled 30–60-minute combined test with both cameras, speech,
      multiple artworks and dashboard monitoring. Once approved/calibrated,
      repeat under motor load.
- [ ] Exercise network/provider/device failures and recover without stale
      answers/frames, duplicate runtimes, unbounded CPU/memory, leaked players,
      sockets or threads. Record FPS, temperature and answer latency.
- [ ] Controlled service restart and cold boot succeed using the installed
      environment/unit. Confirm pan remains off unless separately commissioned.
- [ ] Rehearse rollback and rerun the critical voice/context/camera checks.

## Limits that must remain explicit

- Memory is visit-only and bounded: 12 recent exchanges, up to 96 older ones,
  16 early subject anchors and at most 8,000 characters of earlier prompt
  context; per-turn question/answer excerpts are capped at 500/1,000 characters.
  This is not permanent or unlimited word-for-word memory.
- Silence allowances and capture time are finite. No implementation can promise
  perfect interpretation of every accent, unlimited hesitation or speech
  continuity during a power/network/provider/hardware failure.
- The dashboard's paired log snapshot is synchronized evidence of recorded
  activity, not guaranteed simultaneous real-world playback or invented
  cross-source timestamps. Privacy switches still govern quoted text.
- Software checks do not prove motor power, PWM routing, safe travel, microphone
  capture, real voice quality, camera firmware, school connectivity or cloud
  billing. Those require observed results, not assurances from mock tests.

Only mark the relevant feature deployment-ready after its gate passes on the
actual installation. A pan-disabled workflow/dashboard release is separate from
commissioning the motor and from certifying the complete camera system.
