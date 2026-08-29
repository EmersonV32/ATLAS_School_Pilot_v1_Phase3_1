# ATLAS Codex Final Handoff

This folder preserves the complete, tested handoff. It is the authoritative
source for current ATLAS development and fresh-Jetson recovery.

- `atlas/`: integrated ATLAS application, hardware firmware, recovery tools,
  pinned Jetson dependencies, tests, models, and final engineering dossier.
- `legacy/nationals_2026/`: archived nationals-era source, datasets, weights,
  and hardware experiments retained for recovery and historical reference.

The repository's `archive/atlas/` directory is an earlier application snapshot.
Do not deploy or rebuild from that folder. New work, tests, releases, and
recovery instructions belong under `codex-final-handoff/atlas/`.

Start with `atlas/docs/recovery/REBUILD_FROM_FRESH_FLASH.md` for a clean Jetson
rebuild, or `atlas/docs/handoff/ATLAS_FINAL_HANDOFF.pdf` for the full handoff.
