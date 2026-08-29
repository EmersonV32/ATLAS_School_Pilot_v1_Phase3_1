# ATLAS School Pilot v1.0 — runbook

Who does what, before / during / after a pilot session.

## Roles

- **Operator** (technical): starts ATLAS, holds the admin token, watches
  health.
- **Teacher**: runs the session from the dashboard, chooses profiles,
  handles overrides.

## Day before

- [ ] `python -m pytest -q` passes on the pilot machine.
- [ ] Content pack ingested; `python -m atlas.rag.evaluator` shows no LOW
      categories.
- [ ] `.env` has `ATLAS_ADMIN_TOKEN` (any private value) and — only if the
      school approved cloud answers — `GEMINI_API_KEY` with
      `llm.cloud_llm_enabled: true`.
- [ ] Privacy check: dashboard Privacy panel shows raw audio **off**, raw
      images **off**, face recognition **disabled**, anonymous IDs **on**.
- [ ] If hardware is used: run the relevant stage of
      docs/device_demo_checklist.md.
- [ ] Charge headset; test camera view of the artworks.

## Session start (operator, ~5 min)

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn atlas.dashboard.api:app --host 127.0.0.1 --port 8765
```

- [ ] Open http://127.0.0.1:8765 — health panel all green.
- [ ] Teacher presses *Start session*, sets pack/language/profile.

## During the session (teacher)

- Wrong artwork detected → **Manual override**.
- Mic problems → **Ask ATLAS** typed fallback.
- Any hardware concern → **EMERGENCY STOP** (movement stays blocked until
  the operator clears it with the token).
- "I don't have that detail verified…" answers are ATLAS refusing to guess —
  expected and correct.

## Session end

- [ ] Teacher presses *Stop session*.
- [ ] Operator stops uvicorn (Ctrl+C).
- [ ] Review `data/logs/atlas-<date>.jsonl` for errors and latency spikes.
- [ ] Note artwork misdetections and unanswered questions → feed back into
      the content pack (docs/content_pack_format.md).

## Escalation

1. docs/troubleshooting.md
2. Fall back one rung on the device ladder (mocks always work).
3. Worst case: dev mode + typed questions still demonstrates the full
   retrieval → dialogue → validation pipeline.
