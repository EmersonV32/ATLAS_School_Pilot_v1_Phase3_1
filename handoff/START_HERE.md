# Start here

## Source of truth

The maintained branch is `main`, and the only active ATLAS implementation is
`../atlas/`. Use `codex/` feature branches for reviewed changes; do not deploy
from an old branch merely because a dated handoff names it.

`../archive/` is historical evidence and must not be used as a deployment
source. The handoff directory contains documentation only. The pre-cleanup
state is recoverable at `snapshot/repository-pre-cleanup-2026-10-11`; see
[`../archive/README.md`](../archive/README.md).

## First checks

From the repository root:

```bash
git status --short
git branch --show-current
cd atlas
python scripts/run_deployment_pytest.py
ruff check src tests scripts
python scripts/check_no_secrets.py
python scripts/verify_recovery_bundle.py
python scripts/verify_repository_layout.py
```

Do not edit or deploy until the first two commands confirm which branch and
working-tree changes you inherited. Do not discard changes you did not create.
For a fresh checkout, explicitly select `main`. For an existing dirty checkout,
preserve/review its changes before changing branches. Laptop validation is not
physical-device acceptance.

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

The repository source directory is `atlas/`, but the existing installed Jetson
service uses `/home/super-alex/atlas/ATLAS_School_Pilot_v1_integrated`. Do not
rename the live installation merely to match the GitHub folder or change it
as part of repository cleanup.

When the user explicitly authorizes deployment, use the validated `main`
checkout's `atlas/DEPLOY_ATLAS.ps1`, retain its rollback backup, and then verify
the systemd unit, private environment, audio devices, cameras, headset, and
dashboard. Follow [`jetson/OPERATIONS_MANUAL.md`](jetson/OPERATIONS_MANUAL.md)
for normal operation. No October 11 hardware acceptance is implied by these
documentation changes.

## Non-negotiable boundaries

- Never commit `.env`, API keys, tokens, visitor data, local databases, model
  caches, virtual environments, or generated vector stores.
- Never treat a passing laptop test suite as proof that Jetson hardware works.
- Never deploy from `archive/`.
- Preserve museum-content priority without forcing irrelevant retrieval into a
  general question.
- Keep one TTS provider and voice for an entire spoken response.
