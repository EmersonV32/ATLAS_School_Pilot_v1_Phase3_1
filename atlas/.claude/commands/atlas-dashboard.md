Start the ATLAS teacher dashboard locally:
`python -m uvicorn atlas.dashboard.api:app --host 127.0.0.1 --port 8765`
(run in background). Then verify `GET http://127.0.0.1:8765/health` and
`GET /status` return 200. The dashboard binds to localhost only — do not
expose it on 0.0.0.0. Admin-protected endpoints (content ingest, RAG eval,
clear emergency stop) need the `X-Atlas-Admin-Token` header matching the
`ATLAS_ADMIN_TOKEN` env var. Report the URL and health result when up.
