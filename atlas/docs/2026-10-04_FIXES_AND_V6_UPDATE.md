# October 4 fixes and v6 update preparation

Subsequent user-requested local integration is recorded in
[`2026-10-04_V6_LOCAL_INTEGRATION.md`](2026-10-04_V6_LOCAL_INTEGRATION.md).
V6 is now the active **local** checkpoint and real CPU inference passed. The
preparation-only state described below records the earlier stage, not the
current model selection. No physical deployment occurred at either stage.

Branch: `codex/v6-model-handoff-2026-10-04`. These are local changes; no commit,
push, main merge, firmware flash, or physical deployment was performed.

## Five fixes

1. **Operator authentication:** `/status`, the XIAO camera preview, recent event
   logs, `/ask`, and legacy session controls now require the configured admin
   token. Admin JavaScript sends the header, including on camera blob requests.
   Visitor onboarding, the unlock metadata, public content, and emergency stop
   retain their intended access. Health remains available to the service probe.
2. **Recovery checksum:** `restore_models.sh` reads the release manifest rather
   than an obsolete hard-coded model digest. `--verify-only` performs a local,
   read-only check; LF/CRLF manifests work, and corrupted checkpoints fail.
3. **Camera-outage behavior:** voice processing and session deactivation run
   even without a new camera frame. Capture requests fail safely without a
   frame. Stale visual context is not silently reused during an outage; an
   explicit current-session manual override remains usable.
4. **Session isolation:** generation tokens and short-lived locks stop delayed
   retrieval, LLM/stream responses, microphone recordings, and detections from
   repopulating a later visit. Last answer, manual context and visual history
   clear at session boundaries. A cancelled typed request returns HTTP 409;
   cancelled voice answers do not proceed to TTS.
5. **Deployment rollback:** the uploader runs a separately testable Bash
   transaction with an exit/signal recovery trap covering every post-backup
   step. Rollback restores code, content, model/engine, device configuration and
   the installed service unit. It reloads systemd and respects the previous
   active/stopped state. An incomplete restoration is reported and is not
   restarted. Shell normalization is limited to files in the transaction.

## Validation

- Before the fixes, focused tests reproduced unauthorized access, late memory
  writes, stale recordings and uncleared context. Regression tests now cover
  both denial and authenticated success paths, ordinary and streamed generation,
  delayed retrieval, camera outages, and model corruption.
- The first full gate after the five fixes: **2,947 passed**. The final expanded
  gate, including tracker, CRLF and model-bundle regressions: **2,957 passed**, with
  one existing Starlette/httpx deprecation warning (no test failures).
- Deployment fault injection covers success and failures at stop, extraction,
  pytest, checksum, class verification, export, config restore, unit install,
  daemon reload, start, health and static-asset checks. It uses only temporary
  synthetic files and mocked commands, never the Jetson.
- The uploader's `-PrepareOnly` path is tested without an SSH key. Its archive
  contains the selected checkpoint, corresponding manifest and the new tests;
  it excludes credentials, existing ONNX and TensorRT engines.
- Changed-file Ruff, admin JavaScript syntax, secret scan and recovery verifier
  pass. Repository-wide Ruff has pre-existing violations outside this patch;
  no blanket unrelated formatting/logic rewrite was performed.
- In an isolated mock preview, the complete visitor onboarding worked by
  keyboard at 1024x768 with no browser JavaScript errors. The admin unlock and
  status/content/monitoring requests worked. Reduced-motion CSS was inspected
  in the browser; live reduced-motion emulation was unavailable. Camera and
  headset availability were correctly absent on the laptop.

## Mentor ZIP and model selection

The supplied `ATLAS-v6-trained-results (1).zip` contains the **same** `best.pt`
already preserved under `models/releases/2026-09-28-yolo26n-atlas-v6/`:

`af11b2de376a5c54a1ee11e9765f91ecbf54a1f308a2a82f9106b00a78409731`

`scripts/inspect_yolo_results.py` verifies the ZIP checkpoint against the
evaluation report and the candidate on disk, reads the literal embedded numeric
class dictionary without unpickling, checks all seven labels against ATLAS, and
recomputes the 416/640 aggregate mAP from the per-class AP. It does not execute
the archive's training code or treat document instructions as authorization.

At 416: reported mAP50 **0.964886**, mAP50-95 **0.788704**. These are the mentor's
test-split scores, not measured live accuracy or Jetson performance. All seven
labels match the seven-artwork, 157-chunk content pack. Mona Lisa remains the
weakest class by AP50-95 at 416 (0.573236).

The update workflow can now select this checkpoint **in a prepared archive**
without replacing the active model or contacting any hardware:

```powershell
./scripts/deploy/DEPLOY_ATLAS_VISITOR_IMPROVEMENTS.ps1 -PrepareOnly `
  -YoloCheckpoint models/releases/2026-09-28-yolo26n-atlas-v6/best.pt `
  -PreparedArchivePath C:/path/to/ATLAS-v6-validation-bundle.tar.gz
```

The bundle places the selected bytes at the canonical `models/atlas_yolo.pt`
path and generates its matching manifest. When a separately approved deployment
is eventually run, the transaction verifies the checkpoint's real loader/class
order and builds a **new target-specific** TensorRT FP16 engine at 416; it never
reuses the old engine with the new PT. Rollback retains the old PT/ONNX/engine.
The canonical active local checkpoint remains unchanged, with SHA-256
`5680d3a5fff21d482e579c47f0b19e030b6acbdefdfe5da188de9cc961a66bec`.

## Still required before live promotion

1. Accept checkpoint provenance and load it in an isolated approved ML test
   environment. This laptop venv lacks PyTorch/Ultralytics, so only metadata—not
   inference or compatibility—was validated here. The mentor used Ultralytics
   8.4.163; the recorded Jetson lock uses 8.4.115. Compatibility is unverified;
   do not upgrade protected Jetson packages to assume it away.
2. Evaluate **fresh, session-separated XIAO-camera** footage of all seven works
   plus unrelated art/negative scenes. Predeclare miss/false-alarm limits. Do not
   retune repeatedly on the mentor's locked test split.
3. On the approved target, run the real checkpoint verifier, export at 416,
   compare PT/TensorRT class IDs and boxes on the same fresh frames, and measure
   latency and sustained thermals. No mentor-side engine should be transferred.
4. Obtain explicit physical-deployment approval. The prepared archive is a
   candidate validation artifact, **not** evidence that these gates passed.
