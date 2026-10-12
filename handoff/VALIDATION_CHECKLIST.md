# Validation checklist

For the integrated October 11–12 candidate, start with the
[combined release audit and detailed online checklist](../atlas/docs/2026-10-12_COMBINED_RELEASE_AUDIT.md).
Its known camera firmware defect and pending hardware/cloud tests are not
waived by a passing laptop gate. Keep pan disabled until separate supervised
commissioning. Do not use an old model/firmware deployment bundle blindly for
a workflow-only update.

## Repository gate

- [ ] `git status --short` contains only intended changes.
- [ ] `git ls-files codex-final-handoff` returns no files.
- [ ] No active document or workflow points to the retired
      `codex-final-handoff/atlas` source path.
- [ ] `archive/` contains history only; runtime code does not import it.
- [ ] Secret scan finds no tracked credentials, `.env`, private visitor data,
      local database, generated vector store, or virtual environment.

## Laptop software gate

Run from `atlas/`:

```bash
python scripts/run_deployment_pytest.py
ruff check src tests scripts
python -m compileall -q src scripts tests
python -m pip check
python scripts/check_no_secrets.py
python scripts/verify_recovery_bundle.py
python scripts/verify_repository_layout.py
node scripts/verify_admin_logic.cjs
```

- [ ] Every command exits successfully.
- [ ] Dashboard tests cover both visitor and admin routes.
- [ ] Dialogue, context, TTS-provider locking, headset-button, manual-capture,
      safety, and visitor-profile tests pass.
- [ ] Visitor flow works at 1024x768 landscape, with reduced motion and keyboard
      navigation, without missing assets or console errors.
- [ ] When a local Playwright/Chrome environment is available, run
      `node scripts/verify_admin_browser.cjs <new-QA-output-directory> <Chrome-executable>`
      with intercepted synthetic APIs; validate layouts, controls and recovery.

Use the test wrapper above rather than loading a live installation's `.env`.
It allows synthetic per-test fixtures while blocking real dotenv discovery.
The lint scope covers maintained runtime/tests/scripts, not frozen historical
training recipes. Git-backed gates require new files/deletions to be staged.

## Fresh-clone recovery gate

From a new temporary directory:

```bash
git clone --single-branch --branch main <repository-url> atlas-recovery-test
cd atlas-recovery-test/atlas
python scripts/verify_recovery_bundle.py
python scripts/verify_repository_layout.py
```

- [ ] The verifier passes without relying on ignored files from the development
      machine.
- [ ] Versioned artwork-source hashes match.
- [ ] The checked-out commit equals the intended remote branch or tag.

## Jetson hardware gate

- [ ] Secrets restored outside Git with restrictive permissions.
- [ ] Python environment installs from the locked requirements.
- [ ] Camera enumerates and manual capture returns a current frame.
- [ ] CUDA/TensorRT/PyTorch/model checks pass.
- [ ] Headset input and output devices are selected correctly.
- [ ] Disconnecting and reconnecting the headset refreshes readiness.
- [ ] The multifunction button triggers manual capture once per press.
- [ ] English and Traditional Chinese live speech round trips work.
- [ ] A multi-sentence response uses one voice from start to finish.
- [ ] Two or more dialogue cycles preserve immediate context and discard a
      superseded artwork subject.
- [ ] `atlas.service` starts at boot and survives a controlled restart.
- [ ] Visitor and admin dashboards are reachable from the intended network.
