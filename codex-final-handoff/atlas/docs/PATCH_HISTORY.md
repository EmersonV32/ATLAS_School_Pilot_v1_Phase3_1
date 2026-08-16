# ATLAS Patch History

This file is the permanent record of deployed ATLAS changes. Add one dated entry
for every future patch, including the files changed, validation run, deployment
result, and any remaining limitation. Do not remove older entries.

## 2026-08-16 - Visitor dashboard unified-service refinement

**Scope:** Visitor onboarding at `/` and the existing administrator dashboard at
`/admin`, served by the same ATLAS process on port `8765`.

**Changed:**

- Removed the visitor age minimum and maximum from the numeric entry flow. The
  runtime receives only the existing coarse age-guidance band, never an exact age.
- Kept the expertise artwork panels at their original source aspect ratio and
  enlarged the interest-card imagery without changing the six-card selection flow.
- Removed the placeholder OpenComm2 animation. The headset screen now provides
  written instructions until an approved real video is supplied.
- Made English, French, Spanish, and Italian show as ready in the visitor mock
  preview as well as in the tested device runtime. Arabic and Mandarin remain
  interface previews until their speech support is configured and validated.
- Added `DEPLOY_ATLAS_VISITOR_IMPROVEMENTS.ps1` for a timestamped backup,
  selective upload, focused tests, service restart, and same-port health check.

**Validation:** `246 passed` locally with the full Python test suite on 2026-08-16.
The first Jetson deployment attempt exposed a Python 3.10 `datetime.UTC`
compatibility failure before the service restarted. The patch now uses
`timezone.utc`, and the deployment script rolls back automatically if its
focused validation or restart fails.
The second attempt found an older Jetson admin template and visitor schema. The
deployment now uploads those dashboard dependencies together, rather than
lowering the validation standard.
ATLAS preloads its camera, RAG, speech, and TensorRT model before binding the
dashboard port. The deploy health check now waits up to 50 seconds for that
normal startup sequence instead of rolling back after two seconds.

**Deployment result:** Deployed to the Jetson on 2026-08-16. The Jetson ran
`33 passed` for the focused visitor tests, then the shared service became
healthy on `0.0.0.0:8765`. A final LAN check confirmed `200` responses for both
the visitor page and the authenticated administrator page.

**Remaining limitation:** This patch does not claim Arabic or Mandarin speech
recognition/synthesis support on the Jetson. It leaves those languages visibly
preview-only instead of falsely reporting them as ready.

## Earlier visitor dashboard work in this branch

- `8de293c` - initial visitor dashboard redesign.
- `6c23d3c` - onboarding-flow refinements.
- `fe6132b` - visitor branding and preference-flow refinements.

The commit identifiers above preserve the prior patch trail when their original
date and deployment notes were not captured in this workspace.
