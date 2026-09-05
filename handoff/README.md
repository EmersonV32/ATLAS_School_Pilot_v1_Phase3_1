# ATLAS handoff library

This directory is the current continuity package for another developer, LLM,
museum operator, or replacement Jetson. It describes the active source in
`../atlas/`; it is not a second copy of the runtime.

## Read first

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
- **Project planning:** [`project/NEXT_STEPS_EXECUTION_MATRIX.md`](project/NEXT_STEPS_EXECUTION_MATRIX.md).
