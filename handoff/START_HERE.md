# Start here

## Source of truth

The only active ATLAS implementation in this repository is `../atlas/`.
`../archive/` is historical evidence and must not be used as a deployment
source. The handoff directory contains documentation only.

## First five commands

From the repository root:

```bash
git status --short
git branch --show-current
cd atlas
python -m pytest -q
python scripts/verify_recovery_bundle.py
```

Do not edit or deploy until the first two commands confirm which branch and
working-tree changes you inherited. Do not discard changes you did not create.

## Choose the continuation path

### Another developer or LLM

1. Read [`CURRENT_STATE.md`](CURRENT_STATE.md) and
   [`LLM_HANDOFF.md`](LLM_HANDOFF.md).
2. Read [`architecture/SYSTEM_ARCHITECTURE.md`](architecture/SYSTEM_ARCHITECTURE.md).
3. Run the laptop validation in [`VALIDATION_CHECKLIST.md`](VALIDATION_CHECKLIST.md).
4. Make narrowly scoped changes in `../atlas/` and add tests at the same
   ownership boundary.

### A replacement or freshly flashed Jetson

1. Follow [`jetson/REBUILD_FROM_FRESH_FLASH.md`](jetson/REBUILD_FROM_FRESH_FLASH.md).
2. Restore secrets and private/generated state outside Git as described in
   [`SECRETS_AND_PRIVATE_STATE.md`](SECRETS_AND_PRIVATE_STATE.md).
3. Run both laptop-style tests and the Jetson hardware gate before enabling the
   service.

### An existing Jetson

The GitHub source directory is now `atlas/`, but the installed Jetson service
may continue to use `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`.
Do not rename the live installation merely to match the GitHub folder. Deploy
through the maintained scripts and verify the systemd unit, environment file,
audio devices, camera, headset, and dashboard afterward.

## Non-negotiable boundaries

- Never commit `.env`, API keys, tokens, visitor data, local databases, model
  caches, virtual environments, or generated vector stores.
- Never treat a passing laptop test suite as proof that Jetson hardware works.
- Never deploy from `archive/`.
- Preserve museum-content priority without forcing irrelevant retrieval into a
  general question.
- Keep one TTS provider and voice for an entire spoken response.
