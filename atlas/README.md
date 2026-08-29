# ATLAS runtime

This directory is the single active implementation of the ATLAS wearable AI
museum guide. The repository-level overview is in `../README.md`; continuity,
architecture, operations, privacy, and Jetson recovery documents are in
`../handoff/`.

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
cp .env.example .env                      # Windows: Copy-Item .env.example .env
```

Keep real credentials only in the ignored `.env` file. The optional dependency
groups are `rag`, `vision`, `audio`, `audio-cloud`, `llm`, `dev`, and `all`.

## Verify

```bash
python -m pytest -q
python -m compileall -q src scripts
python -m pip check
python scripts/check_no_secrets.py
python scripts/verify_recovery_bundle.py
```

These commands validate the laptop-safe software and repository recovery
bundle. They do not prove camera, headset, CUDA/TensorRT, network-provider, or
systemd behavior on the Jetson. Use `../handoff/VALIDATION_CHECKLIST.md` for
the physical acceptance gate.

## Run

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

Fresh Jetson recovery starts at
`../handoff/jetson/REBUILD_FROM_FRESH_FLASH.md`. The maintained incremental
visitor/runtime deployment script is
`scripts/deploy/DEPLOY_ATLAS_VISITOR_IMPROVEMENTS.ps1` and accepts
`-SshKeyPath` or the `ATLAS_SSH_KEY` environment variable. Never commit the
key, `.env`, live databases, logs, recordings, generated vector stores, model
caches, or target-specific TensorRT artifacts.

## Documentation

- `../handoff/START_HERE.md`
- `../handoff/DEVELOPER_GUIDE.md`
- `../handoff/architecture/SYSTEM_ARCHITECTURE.md`
- `../handoff/TROUBLESHOOTING.md`
- `../handoff/CONTENT_PACK_FORMAT.md`

Historical snapshots and one-time utilities are under `../archive/` and are
not deployment inputs.
