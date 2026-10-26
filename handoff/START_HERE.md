# Start here

## Source of truth

For the October 26 teammate takeover, start with the
[two-week handoff](2026-10-26_TEAMMATE_HANDOFF.md) and give a new Codex the
[continuation prompt](NEW_CODEX_PROMPT.md). Read both
[repository](../AGENTS.md) and [application](../atlas/AGENTS.md) instructions.

The current continuation branch is `codex/camera-offline-demo-2026-10-25`;
its latest working fixes have not been promoted to `main`. The only active
ATLAS implementation is `../atlas/`.

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
For a fresh checkout, explicitly select the continuation branch above using
the clone command in the current handoff. For an existing dirty checkout,
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

When the present human operator explicitly authorizes deployment, coordinate
with any peer chat and follow the
[source-only deployment/rollback runbook](DEPLOYMENT_RUNBOOK.md). Do not use
the broad installer for an ordinary source update. Follow the
[operations manual](jetson/OPERATIONS_MANUAL.md) for normal operation.
Documentation publication does not authorize or perform a device change.

## Non-negotiable boundaries

- Never commit `.env`, API keys, tokens, visitor data, local databases, model
  caches, virtual environments, or generated vector stores.
- Never treat a passing laptop test suite as proof that Jetson hardware works.
- Never deploy from `archive/`.
- Keep SG90 pan disabled: commissioning is paused without successful movement.
- Transfer credentials and admin/safety codes privately between humans;
  never read or publish them in Git or chat.
- Preserve museum-content priority without forcing irrelevant retrieval into a
  general question.
- Keep one TTS provider and voice for an entire spoken response.
