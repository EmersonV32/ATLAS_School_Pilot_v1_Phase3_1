# Validation checklist

Start with the [October 26 handoff](2026-10-26_TEAMMATE_HANDOFF.md) and
[source-only deployment runbook](DEPLOYMENT_RUNBOOK.md). Older onsite/audit
reports are dated evidence, not current deployment commands. Passing laptop
checks does not waive physical acceptance. SG90 commissioning is paused;
pan is not required to make the conversation demo ready.

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

### Windows: isolated temporary directories and focused runs

Some Windows environments deny access to pytest's default temporary directory.
Use a new temporary root for each process; do not repeatedly retry a known
inaccessible directory or weaken tests. From `atlas/` in PowerShell:

```powershell
$atlasQaRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("atlas-qa-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $atlasQaRoot -ErrorAction Stop | Out-Null
$env:TEMP = $atlasQaRoot
$env:TMP = $atlasQaRoot
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'scripts'); import run_deployment_pytest as gate; original=gate.pytest.main; gate.pytest.main=lambda args: original(args+sys.argv[2:]+['--basetemp='+sys.argv[1],'--tb=short','--maxfail=3']); raise SystemExit(gate.run_tests())" (Join-Path $atlasQaRoot "pytest")
```

Append specific `tests/test_*.py` paths to that command for focused runs. With
no paths it runs the full suite. Use the approved host Python execution context
if the restricted runner still cannot access the new directory. Deployment
transaction tests can take several minutes. When splitting the suite across
processes, use distinct temporary roots and record that their union covers
every test file exactly once; a focused subset is not the full gate.

## Fresh-clone recovery gate

From a new temporary directory:

```bash
git clone --single-branch --branch codex/camera-offline-demo-2026-10-25 <repository-url> atlas-recovery-test
cd atlas-recovery-test/atlas
python scripts/verify_recovery_bundle.py
python scripts/verify_repository_layout.py
```

- [ ] The verifier passes without relying on ignored files from the development
      machine.
- [ ] Versioned artwork-source hashes match.
- [ ] The checked-out commit equals the intended remote branch or tag.

## Jetson hardware gate

Apply only the checks relevant to the approved change, and record remaining
checks as pending. For the camera-free conversation demo, the damaged primary
camera may remain degraded; do not require capture or flash firmware merely
to start a voice session. A camera feature still requires its own fresh-frame,
capture, button, and load acceptance. SG90 motion needs a separate supervised
commissioning plan and is currently paused. Do not install packages or restore
secrets on an already working device just to repeat this list.

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
