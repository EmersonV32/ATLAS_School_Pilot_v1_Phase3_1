"""ATLAS visitor and operator dashboards served by local FastAPI.

Run locally (never expose publicly):
    python -m uvicorn atlas.dashboard.api:app --host 127.0.0.1 --port 8765

Protected endpoints require the X-Atlas-Admin-Token header matching the
environment variable configured by settings.dashboard.admin_token_env.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from atlas.app.dependency_container import Container, build_container
from atlas.dashboard.auth import make_admin_guard
from atlas.dashboard.runtime_service import RuntimeService
from atlas.dashboard.schemas import (
    AdminDemoStartRequest,
    AskRequest,
    AskResponse,
    AudioOutputRequest,
    DashboardConfigUpdate,
    DemoSimulateRequest,
    IngestRequest,
    ManualArtworkRequest,
    SessionProfileRequest,
)
from atlas.dashboard.visitor_schemas import (
    VisitorHelpRequest,
    VisitorProgressRequest,
    VisitorSimulationRequest,
)
from atlas.dashboard.visitor_service import VisitorService

_STATIC_DIR = Path(__file__).parent / "static"
_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(
    container: Container | None = None,
    capture_request: Callable[[], None] | None = None,
    visitor_service: VisitorService | None = None,
) -> FastAPI:
    container = container or build_container()
    service = RuntimeService(container, capture_request=capture_request)
    dashboard_settings = container.settings.dashboard
    loopback_hosts = {"127.0.0.1", "localhost", "::1"}
    if not dashboard_settings.admin_auth_required:
        if dashboard_settings.host not in loopback_hosts:
            raise RuntimeError(
                "admin authentication can be disabled only on a loopback host"
            )

        def require_admin() -> None:
            return None
    else:
        require_admin = make_admin_guard(dashboard_settings.admin_token_env)

    app = FastAPI(
        title="ATLAS Operations Console",
        description="Local operator controls for ATLAS.",
        version="1.1.0",
    )
    app.state.service = service
    # Laptop/dev mode remains mock-backed. On the Jetson, the visitor flow and
    # DeviceRuntime share this exact RuntimeService instance and session ID.
    app.state.visitor_service = visitor_service or VisitorService(
        runtime_service=(service if container.settings.mode.value == "device" else None)
    )
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    # -- pages --------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return (_TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")

    @app.get("/admin", response_class=HTMLResponse)
    def admin() -> str:
        return (_TEMPLATES_DIR / "admin.html").read_text(encoding="utf-8")

    @app.get("/service-worker.js", response_class=FileResponse)
    def service_worker() -> FileResponse:
        return FileResponse(
            _STATIC_DIR / "service-worker.js",
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-cache",
                "Service-Worker-Allowed": "/",
            },
        )

    @app.get("/admin/access")
    def admin_access() -> dict:
        return {"auth_required": dashboard_settings.admin_auth_required}

    # -- visitor onboarding (mock in dev, runtime-backed on device) --------
    @app.get("/api/visitor/bootstrap")
    def visitor_bootstrap() -> dict:
        return app.state.visitor_service.bootstrap()

    @app.post("/api/visitor/onboarding/progress")
    def visitor_progress(req: VisitorProgressRequest) -> dict:
        try:
            return app.state.visitor_service.progress(req)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/visitor/readiness")
    def visitor_readiness() -> dict:
        return app.state.visitor_service.readiness()

    @app.post("/api/visitor/onboarding/start")
    def visitor_start() -> dict:
        try:
            return app.state.visitor_service.start()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/visitor/help")
    def visitor_help(req: VisitorHelpRequest) -> dict:
        return app.state.visitor_service.request_help(req)

    @app.post("/api/visitor/reset")
    def visitor_reset() -> dict:
        return app.state.visitor_service.reset()

    # -- privacy-bounded visitor monitoring (operator only) ----------------
    @app.get("/api/admin/live-status", dependencies=[Depends(require_admin)])
    def visitor_live_status() -> dict:
        return app.state.visitor_service.live_status()

    @app.post(
        "/api/admin/help/{request_id}/acknowledge",
        dependencies=[Depends(require_admin)],
    )
    def acknowledge_visitor_help(request_id: str) -> dict:
        try:
            return app.state.visitor_service.acknowledge_help(request_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/admin/session/stop", dependencies=[Depends(require_admin)])
    def stop_visitor_session() -> dict:
        return app.state.visitor_service.stop()

    @app.post("/api/admin/demo/start", dependencies=[Depends(require_admin)])
    def start_admin_demo(req: AdminDemoStartRequest) -> dict:
        try:
            return app.state.visitor_service.start_demo(
                language=req.language,
                profile=req.profile,
                pack_id=req.pack_id,
                accessibility_mode=req.accessibility_mode,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/admin/audio", dependencies=[Depends(require_admin)])
    def admin_audio_status() -> dict:
        return service.audio_status()

    @app.put("/api/admin/audio", dependencies=[Depends(require_admin)])
    def update_admin_audio(req: AudioOutputRequest) -> dict:
        try:
            return service.set_audio_output(
                route=req.route,
                volume_percent=req.volume_percent,
            )
        except (LookupError, RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/admin/audio/test", dependencies=[Depends(require_admin)])
    def test_admin_audio() -> dict:
        try:
            return service.test_audio_output()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/admin/visitor/simulate", dependencies=[Depends(require_admin)])
    def simulate_visitor(req: VisitorSimulationRequest) -> dict:
        return app.state.visitor_service.simulate(req.scenario)

    # -- health / status ----------------------------------------------------
    @app.get("/health")
    def health() -> dict:
        return service.health()

    @app.get("/status")
    def status() -> dict:
        return service.status()

    @app.get("/camera/frame.jpg", response_class=Response)
    def camera_frame() -> Response:
        try:
            frame = service.camera_frame_jpeg()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return Response(
            content=frame,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )

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

    @app.post("/session/capture")
    def capture_artwork() -> dict:
        try:
            return service.capture_artwork()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    # -- typed-question fallback -------------------------------------------
    @app.post("/ask", response_model=AskResponse)
    def ask(req: AskRequest) -> AskResponse:
        return AskResponse(
            **service.ask(req.question, language=req.language, profile=req.profile)
        )

    # -- content ------------------------------------------------------------
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

    # -- operator configuration --------------------------------------------
    @app.get("/admin/config", dependencies=[Depends(require_admin)])
    def admin_config() -> dict:
        return service.dashboard_config()

    @app.put("/admin/config", dependencies=[Depends(require_admin)])
    def update_admin_config(req: DashboardConfigUpdate) -> dict:
        try:
            return service.save_dashboard_config(req.model_dump(exclude_none=True))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # -- logs ---------------------------------------------------------------
    @app.get("/logs/recent")
    def logs_recent(limit: int = 50) -> list[dict]:
        return service.recent_logs(limit=min(max(limit, 1), 200))

    @app.get("/logs/runtime", dependencies=[Depends(require_admin)])
    def logs_runtime(limit: int = 250) -> dict:
        return service.runtime_logs(limit=min(max(limit, 1), 1000))

    @app.get("/logs/runtime/human", dependencies=[Depends(require_admin)])
    def logs_runtime_human(limit: int = 250) -> dict:
        return service.human_runtime_logs(limit=min(max(limit, 1), 1000))

    @app.get("/logs/recent/human")
    def logs_recent_human(limit: int = 50) -> list[dict]:
        return service.human_recent_logs(limit=min(max(limit, 1), 200))

    # -- hardware -----------------------------------------------------------
    @app.post("/hardware/emergency-stop")
    def emergency_stop() -> dict:
        return service.emergency_stop()

    @app.post(
        "/hardware/clear-emergency-stop", dependencies=[Depends(require_admin)]
    )
    def clear_emergency_stop() -> dict:
        return service.clear_emergency_stop()

    # -- demo controls ------------------------------------------------------
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
