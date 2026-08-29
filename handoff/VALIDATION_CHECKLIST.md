# Validation checklist

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
python -m pytest -q
python -m compileall -q src scripts
python -m pip check
python scripts/verify_recovery_bundle.py
```

- [ ] Every command exits successfully.
- [ ] Dashboard tests cover both visitor and admin routes.
- [ ] Dialogue, context, TTS-provider locking, headset-button, manual-capture,
      safety, and visitor-profile tests pass.

## Fresh-clone recovery gate

From a new temporary directory:

```bash
git clone <repository-url> atlas-recovery-test
cd atlas-recovery-test/atlas
python scripts/verify_recovery_bundle.py
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
