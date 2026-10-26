# ATLAS repository instructions

## Teammate continuation (2026-10-26)

- Read `handoff/START_HERE.md`, `handoff/2026-10-26_TEAMMATE_HANDOFF.md`,
  and `handoff/DEPLOYMENT_RUNBOOK.md` before changing this project.
- Continue from `codex/camera-offline-demo-2026-10-25`; its later fixes have
  not been promoted to `main`. Preserve inherited edits before switching refs.
- The teammate operating the device can authorize scoped work. A handoff is
  not standing approval to deploy, restart, change networking, or move hardware.
- SG90 commissioning is paused without successful physical movement. Do not
  enable pan or bypass its safety gates as part of software/demo work.
- Credentials and admin/safety codes must be transferred privately between
  humans, never recorded in Git, chat, or agent-readable handoff material.

## Source of truth

- The maintained application is `atlas/`. Implement, test, and deploy current
  work only from that directory.
- `handoff/` contains current manuals and continuity information, but no second
  runtime copy.
- `archive/` is dated historical reference only. Do not import, deploy, or
  modify archived code for current application or dashboard work.

## Git and delivery

- Work on a `codex/` feature branch and never force-push. Update `main` only
  when the user explicitly requests it and the full validation gate passes.
- Do not deploy to physical hardware without explicit user approval.
- Keep documentation, implementation, integration, and hardening changes in
  reviewable commits.
- Run `python scripts/verify_recovery_bundle.py` from `atlas/` before publishing
  a recovery-affecting change.

## Safety

- Never read, print, edit, or commit `.env`, credentials, private keys,
  visitor logs, generated databases, or raw media.
- Never modify Jetson/L4T packages, package holds, firmware, EV3 calibration,
  battery wiring, or live service configuration during dashboard work.
- The recovered Jetson must not receive a generic `apt upgrade`.

