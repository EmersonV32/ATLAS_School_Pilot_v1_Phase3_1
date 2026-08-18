# ATLAS Codex admin copilot

## Purpose

The private `/admin` dashboard includes an approval-gated Codex operations
copilot. It can inspect privacy-safe runtime state, run the existing RAG
evaluation, propose content re-indexing or validated configuration changes,
prepare an unpublished artwork intake draft, and create a handoff for code or
deployment work.

The copilot is optional and disabled by default. The visitor experience does
not depend on it.

## Safety boundary

Codex receives only a bounded snapshot containing component health, anonymous
session state, artwork state, content-pack metadata, and editable non-secret
configuration. It does not receive visitor prompts, transcripts, raw media,
names, exact ages, credentials, or private logs.

The model has no shell, filesystem, Git, SSH, deployment, emergency-stop, or
arbitrary HTTP tool. It can select only these server-owned operations:

| Operation | Execution |
| --- | --- |
| Answer/explain | Immediate |
| Inspect privacy-safe system state | Immediate |
| Run the existing read-only RAG evaluation | Immediate |
| Re-index an existing content pack | Separate admin approval required |
| Update validated dashboard configuration | Separate admin approval required |
| Create an unpublished artwork intake draft | Separate admin approval required |
| Request code/deployment work | Handoff only; never executed in the dashboard |

The original operator request is held only for the API call and is not stored
in job history or ATLAS logs. Audit events contain only the job identifier,
allowlisted action name, and status. Likely credential values are rejected
before a request is sent to OpenAI.

## Installation and configuration

Install the optional SDK alongside the existing application:

```bash
python -m pip install -e ".[admin-ai]"
```

Set secrets in the service environment, never in committed YAML or source:

```bash
export ATLAS_ADMIN_TOKEN="generate-a-strong-random-admin-token"
export ATLAS_ADMIN_AI_ENABLED=true
export OPENAI_API_KEY="set-this-outside-git"
```

PowerShell for a local development session:

```powershell
$env:ATLAS_ADMIN_TOKEN = "generate-a-strong-random-admin-token"
$env:ATLAS_ADMIN_AI_ENABLED = "true"
$env:OPENAI_API_KEY = "set-this-outside-git"
python -m uvicorn atlas.dashboard.api:app --host 127.0.0.1 --port 8765
```

The default model is `gpt-5.3-codex`. Override it without editing repository
configuration when account availability requires another Codex model:

```bash
export ATLAS_ADMIN_AI_MODEL="gpt-5.3-codex"
```

Open `http://127.0.0.1:8765/admin`, enter the admin token, and select
**Unlock**. The Ask Codex panel will show the active model when ready.

## API contract

Every route below requires the normal `X-Atlas-Admin-Token` header.

- `GET /api/admin/ai/status` returns availability, model, mode, and capability
  names. It never returns a key.
- `GET /api/admin/ai/jobs` returns the bounded in-memory job history. Operator
  requests are absent.
- `POST /api/admin/ai/jobs` accepts `{"request": "..."}` and returns either an
  immediate result, an approval proposal, or a code-work handoff.
- `POST /api/admin/ai/jobs/{job_id}/approve` executes one exact validated
  pending mutation. Repeated approval after completion is idempotent.
- `POST /api/admin/ai/jobs/{job_id}/reject` rejects a pending mutation without
  executing it.

Job history is intentionally in memory and clears on service restart. The
privacy-safe audit trail remains in the existing structured ATLAS event log.

## Artwork workflow

An approved artwork request creates an `unverified_draft` JSON file under the
configured data directory's `admin_ai_drafts/` folder. It does not alter the
content-pack manifest, publish RAG chunks, or modify the vision model.

Publishing an artwork still requires:

1. Human source and copyright review.
2. Source-attributed, student-safe content chunks.
3. Content validation, ingestion, and RAG evaluation.
4. Labeled recognition images and YOLO training/export.
5. Physical recognition validation using the Jetson camera.

This separation prevents a fluent model response from being treated as a
verified museum record or a trained camera class.

## Jetson deployment note

Dashboard implementation and Jetson deployment remain separate review gates.
Do not place the OpenAI key in Git, dashboard configuration, browser storage,
or an admin prompt. Do not give the web process unrestricted sudo or SSH
credentials. Installing this optional Python extra does not authorize Jetson
package upgrades, firmware changes, service restarts, or deployment.
