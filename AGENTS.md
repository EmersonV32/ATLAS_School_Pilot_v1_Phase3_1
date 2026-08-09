# ATLAS repository instructions

## Source of truth

- The maintained application is `codex-final-handoff/atlas/`.
- The root `atlas/` directory is an outdated historical copy. Do not implement
  new work there.
- `legacy/` is reference and training history only. Do not modify it for
  application or dashboard work.

## Git and delivery

- Work on a `codex/` feature branch. Never force-push or push directly to
  `main`.
- Do not merge or deploy without explicit user approval.
- Keep documentation, implementation, integration, and hardening changes in
  reviewable commits.

## Safety

- Never read, print, edit, or commit `.env`, credentials, private keys,
  visitor logs, generated databases, or raw media.
- Never modify Jetson/L4T packages, package holds, firmware, EV3 calibration,
  battery wiring, or live service configuration during dashboard work.
- The recovered Jetson must not receive a generic `apt upgrade`.

