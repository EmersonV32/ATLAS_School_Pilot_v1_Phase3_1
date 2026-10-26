# ATLAS runtime

This directory is the single active implementation of the ATLAS wearable AI
museum guide. The repository-level overview is in `../README.md`; continuity,
architecture, operations, privacy, and Jetson recovery documents are in
`../handoff/`.

For the October 26 teammate takeover, read the
[current handoff](../handoff/2026-10-26_TEAMMATE_HANDOFF.md) and
[new Codex prompt](../handoff/NEW_CODEX_PROMPT.md). Continue from
`codex/camera-offline-demo-2026-10-25`; its later fixes are not on `main` yet.

## Requirements

- Python 3.10 or newer
- Core development requires no Jetson, camera, audio hardware, provider key,
  or downloaded ML model.
- Device mode requires the dependencies and hardware described in
  `../handoff/jetson/REBUILD_FROM_FRESH_FLASH.md`.

## Laptop setup

```bash
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Mock development needs no private `.env`. Never read or overwrite an inherited
environment file; humans configure real credentials privately. The optional dependency
groups are `rag`, `vision`, `audio`, `audio-cloud`, `llm`, `dev`, and `all`.
The optional `camera-pan` group is only for the retained PCA9685 backend;
[direct SG90 camera pan](docs/CAMERA_PAN.md) needs no additional Python package.

## Verify

```bash
python scripts/run_deployment_pytest.py
ruff check src tests scripts
python -m compileall -q src scripts
python -m pip check
python scripts/check_no_secrets.py
python scripts/verify_recovery_bundle.py
python scripts/verify_repository_layout.py
```

These commands validate the laptop-safe software and repository recovery
bundle. They do not prove camera, headset, CUDA/TensorRT, network-provider, or
systemd behavior on the Jetson. Use `../handoff/VALIDATION_CHECKLIST.md` for
the physical acceptance gate.

## Run

These commands are for an isolated laptop development checkout without private
device configuration. Do not launch a second runtime on the installed Jetson.

Run mock pipeline cycles:

```bash
python -m atlas.app.main --mode dev --run 3
```

Start the visitor and staff dashboards:

```bash
python -m uvicorn atlas.dashboard.api:app --host 127.0.0.1 --port 8765
```

- Visitor setup: `http://127.0.0.1:8765/`
- Staff dashboard: `http://127.0.0.1:8765/admin`

Ingest or evaluate the demo content pack:

```bash
python -m atlas.rag.ingest --pack data/content_packs/demo_pack --mode dev --reset
python scripts/evaluate_rag.py
```

## Layout

```text
artwork-source/   Versioned original artwork assets and hashes
config/           Runtime, hardware, and visitor-profile configuration
data/             Versioned content packs plus ignored generated runtime state
ev3/              EV3 integration files
firmware/         XIAO camera firmware and non-secret templates
models/           Portable tracked model assets and integrity manifest
scripts/          Startup, deployment, diagnostics, and recovery tools
src/atlas/        Installable Python package
tests/            Laptop-safe automated tests
```

Important package boundaries:

- `app/` and `pipeline/`: lifecycle, events, state, and conversation cycles
- `vision/`: camera, detection, tracking, and manual capture
- `audio/`: speech recognition, synthesis, playback, and fallbacks
- `rag/` and `dialogue/`: retrieval, context, safety, and response generation
- `dashboard/`: FastAPI API, runtime bridge, visitor UI, and staff UI
- `storage/`: local event and session persistence
- `hardware/`: mock and EV3 hardware adapters

## Deployment

For an explicitly approved update to the working device, follow the
[source-only deployment and rollback runbook](../handoff/DEPLOYMENT_RUNBOOK.md).
Use `scripts/deploy/source_release.py`; the older broad `DEPLOY_ATLAS.ps1`
installer can also change models, firmware, and the service unit. Fresh Jetson
recovery is a separate project starting at the
[rebuild guide](../handoff/jetson/REBUILD_FROM_FRESH_FLASH.md). Never commit
keys, `.env`, live databases, logs, recordings, generated vector stores,
model caches, or target-specific TensorRT artifacts.

## Documentation

- `../handoff/START_HERE.md`
- `../handoff/DEVELOPER_GUIDE.md`
- `../handoff/architecture/SYSTEM_ARCHITECTURE.md`
- `../handoff/TROUBLESHOOTING.md`
- `../handoff/CONTENT_PACK_FORMAT.md`

Historical snapshots and one-time utilities are under `../archive/` and are
not deployment inputs.
