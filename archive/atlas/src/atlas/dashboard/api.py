"""ATLAS teacher/operator dashboard — local FastAPI app.

Run locally (never expose publicly):
    python -m uvicorn atlas.dashboard.api:app --host 127.0.0.1 --port 8765

Protected endpoints (content ingest, RAG eval, demo simulation, clear
emergency stop) require the X-Atlas-Admin-Token header matching the env
var named by settings.dashboard.admin_token_env (default ATLAS_ADMIN_TOKEN).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from atlas.app.dependency_container import Container, build_container
from atlas.dashboard.auth import make_admin_guard
from atlas.dashboard.runtime_service import RuntimeService
from atlas.dashboard.schemas import (
    AskRequest,
    AskResponse,
    DemoSimulateRequest,
    IngestRequest,
    ManualArtworkRequest,
    SessionProfileRequest,
)

_STATIC_DIR = Path(__file__).parent / "static"
_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(container: Container | None = None) -> FastAPI:
    container = container or build_container()
    service = RuntimeService(container)
    require_admin = make_admin_guard(container.settings.dashboard.admin_token_env)

    app = FastAPI(
        title="ATLAS Teacher Dashboard",
        description="Atlas — because every story deserves a listener.",
        version="1.0.0",
    )
    app.state.service = service

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    # -- pages ------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (_TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")

    # -- health / status ----------------------------------------------------
    @app.get("/health")
    def health() -> dict:
        return service.health()

    @app.get("/status")
    def status() -> dict:
        return service.status()

    # -- session ------------------------------------------------------------
    @app.post("/session/start")
    def session_start() -> dict:
        return service.start_session()

    @app.post("/session/stop")
    def session_stop() -> dict:
        return service.stop_session()

    @app.post("/session/profile")
    def session_profile(req: SessionProfileRequest) -> dict:
        return service.set_profile(
            language=req.language,
            profile=req.profile,
            pack_id=req.pack_id,
            accessibility_mode=req.accessibility_mode,
        )

    @app.post("/session/manual-artwork")
    def manual_artwork(req: ManualArtworkRequest) -> dict:
        try:
            return service.set_manual_artwork(req.artwork_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete("/session/manual-artwork")
    def clear_manual_artwork() -> dict:
        return service.clear_manual_artwork()

    # -- typed-question fallback ---------------------------------------------
    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest) -> AskResponse:
        return AskResponse(
            **service.ask(req.question, language=req.language, profile=req.profile)
        )

    # -- content ---------------------------------------------------------------
    @app.get("/content/packs")
    def content_packs() -> list[dict]:
        return service.content_packs()

    @app.get("/artworks")
    def artworks() -> list[dict]:
        return service.artworks()

    @app.post("/content/ingest", dependencies=[Depends(require_admin)])
    def content_ingest(req: IngestRequest) -> dict:
        try:
            return service.ingest_pack(req.pack_id, reset=req.reset)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/eval/rag", dependencies=[Depends(require_admin)])
    def eval_rag() -> dict:
        return service.run_rag_eval()

    # -- logs ---------------------------------------------------------------
    @app.get("/logs/recent")
    def logs_recent(limit: int = 50) -> list[dict]:
        return service.recent_logs(limit=min(max(limit, 1), 200))

    # -- hardware ---------------------------------------------------------------
    @app.post("/hardware/emergency-stop")
    def emergency_stop() -> dict:
        # Deliberately unauthenticated: stopping must never be gated.
        return service.emergency_stop()

    @app.post(
        "/hardware/clear-emergency-stop", dependencies=[Depends(require_admin)]
    )
    def clear_emergency_stop() -> dict:
        return service.clear_emergency_stop()

    # -- demo controls (dev/demo mode only) -----------------------------------
    @app.post("/demo/simulate", dependencies=[Depends(require_admin)])
    def demo_simulate(req: DemoSimulateRequest) -> dict:
        try:
            return service.demo_simulate(req.scenario)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()
