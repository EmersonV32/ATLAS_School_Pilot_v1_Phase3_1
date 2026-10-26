# ATLAS handoff library

This directory is the current continuity package for another developer, LLM,
museum operator, or replacement Jetson. It describes the active source in
`../atlas/`; it is not a second copy of the runtime.

## Current authority

For the October 26 teammate takeover, continue from
`codex/camera-offline-demo-2026-10-25`. Its latest fixes are not on `main` yet;
do not start from `main` and lose those changes. The only active runtime is
[`../atlas/`](../atlas/). Publish reviewed feature-branch commits without
force-pushing; promotion to `main` needs an explicit request and validation.
Documentation publication does not deploy to or validate the Jetson.

The latest operating observations remain dated in
[`CURRENT_STATE.md`](CURRENT_STATE.md). The October 4 model handoff,
[`2026-10-04_NEW_CHAT.md`](2026-10-04_NEW_CHAT.md), describes an earlier
continuation stage, not a requirement to keep using that feature branch.

## Read first

**Current takeover:** [two-week handoff](2026-10-26_TEAMMATE_HANDOFF.md),
[new Codex prompt](NEW_CODEX_PROMPT.md), and
[deployment/rollback runbook](DEPLOYMENT_RUNBOOK.md).

1. [`START_HERE.md`](START_HERE.md) - authority, first commands, and the safest
   continuation path.
2. [`CURRENT_STATE.md`](CURRENT_STATE.md) - what is implemented, what has been
   verified, and what still requires the physical Jetson.
3. [`REPOSITORY_MAP.md`](REPOSITORY_MAP.md) - where every class of file belongs.
4. [`VALIDATION_CHECKLIST.md`](VALIDATION_CHECKLIST.md) - gates before merging,
   deploying, or calling a recovery complete.
5. [`SECRETS_AND_PRIVATE_STATE.md`](SECRETS_AND_PRIVATE_STATE.md) - what must be
   restored outside Git.

## By role

- **Another LLM or developer:** [`LLM_HANDOFF.md`](LLM_HANDOFF.md), then
  [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) and
  [`architecture/`](architecture/).
- **Replacement Jetson:** [`jetson/REBUILD_FROM_FRESH_FLASH.md`](jetson/REBUILD_FROM_FRESH_FLASH.md),
  then [`jetson/OPERATIONS_MANUAL.md`](jetson/OPERATIONS_MANUAL.md). For the
  separate CSI preview camera, use
  [`jetson/ARDUCAM_IMX477.md`](jetson/ARDUCAM_IMX477.md).
- **Museum/demo operator:** [`operations/`](operations/) and
  [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md).
- **Privacy reviewer:** [`policies/`](policies/).
- **Visitor-dashboard developer:** [`visitor-dashboard/`](visitor-dashboard/).
- **Content editor:** [`CONTENT_PACK_FORMAT.md`](CONTENT_PACK_FORMAT.md).
- **Project planning:** [`project/NEXT_STEPS_EXECUTION_MATRIX.md`](project/NEXT_STEPS_EXECUTION_MATRIX.md)
  and the [`competition binder`](../comp_info/README.md).
- **Camera and school/hotspot networking:**
  [`camera firmware guide`](../atlas/firmware/xiao_camera/README.md) and
  [`school Wi-Fi setup`](../atlas/docs/SCHOOL_WIFI_SETUP.md).
- **YOLO model/recovery evidence:** [`model index`](../atlas/models/README.md).
- **Earlier implementations:** [`historical archive index`](../archive/README.md),
  including the pre-cleanup recovery tag. Historical instructions are evidence,
  not commands to execute against today's system.
