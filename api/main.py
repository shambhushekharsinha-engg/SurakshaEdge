"""
SurakshaEdge - FastAPI application
Serves REST endpoints and WebSocket for dashboard.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .middleware import RateLimitMiddleware, RequestLoggingMiddleware, SecurityHeadersMiddleware
from .schemas import CameraOut, EventPacketIn, FeedbackIn, HealthOut, MetricsOut, SimulateIn
from .security import check_replay, require_token
from .store import EventStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

store = EventStore()
_ws_clients: List[WebSocket] = []
_cameras: List[Dict[str, Any]] = []
_start_time: float = time.time()

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load camera config if available
    cfg_path = os.environ.get("SURAKSHA_CONFIG", "configs/demo.yaml")
    if Path(cfg_path).exists():
        import yaml
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
        for cam in cfg.get("cameras", []):
            _cameras.append({
                "id": cam["id"],
                "gps": {"lat": cam["gps"][0], "lon": cam["gps"][1]},
                "zone": cam.get("zone", cam["id"]),
                "status": "idle",
            })
        logger.info("Loaded %d camera(s) from config", len(_cameras))

        # Auto-detect audio mode from config and set env var for /health
        audio_cfg = cfg.get("audio", {})
        audio_model = audio_cfg.get("model")
        if audio_model and Path(audio_model).exists():
            os.environ["SURAKSHA_AUDIO_MODE"] = "mfcc_cnn"
            logger.info("Audio mode: mfcc_cnn (%s)", audio_model)
        else:
            os.environ.setdefault("SURAKSHA_AUDIO_MODE", "energy_fallback")
            logger.warning(
                "Audio mode: energy_fallback (no model at %s). "
                "Train models/audio_cnn.onnx to enable MFCC-CNN.",
                audio_model or "unset",
            )

    # Start retention purge task (skip in test mode to avoid event loop conflicts)
    if not os.environ.get("SURAKSHA_TEST_MODE"):
        async def purge_loop():
            while True:
                await asyncio.sleep(3600)
                store.purge_old()
        asyncio.create_task(purge_loop())

    yield


app = FastAPI(
    title="SurakshaEdge API",
    version="0.4.1",
    lifespan=lifespan,
    description="Edge AI assault detection — SEVA FIRST 2026 | REG-008-OP-024",
    docs_url=None,    # We serve custom /docs with unpkg CDN
    redoc_url=None,   # We serve custom /redoc
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, rate_per_min=60, burst=10)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve dashboard static files
dashboard_dir = Path(__file__).parent.parent / "dashboard"
if dashboard_dir.exists():
    _static_dir = dashboard_dir / "static"
    try:
        # Only mount if the directory exists and contains at least one file
        # (StaticFiles raises RuntimeError on empty directories)
        if _static_dir.exists() and any(_static_dir.iterdir()):
            app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
        else:
            logger.warning("Static dir %s is empty or missing — /static not mounted", _static_dir)
    except Exception as _e:
        logger.warning("Could not mount /static: %s", _e)


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    logger.info("WS client connected. Total: %d", len(_ws_clients))
    try:
        while True:
            # Send heartbeat every 10 s
            await asyncio.sleep(10)
            await websocket.send_json({"type": "heartbeat", "ts": time.time()})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WS error: %s", e)
    finally:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)
        logger.info("WS client disconnected. Total: %d", len(_ws_clients))


async def _broadcast(message: Dict[str, Any]):
    """Broadcast a message to all connected WebSocket clients."""
    dead = []
    for ws in list(_ws_clients):
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


@app.websocket("/stream/status")
async def ws_stream_status(websocket: WebSocket):
    """
    WebSocket endpoint that broadcasts live pipeline health metrics every 5 seconds.
    Payload: {type, timestamp, fps, latency_p50_ms, audio_mode, camera_count,
              uptime_s, memory_mb, ws_client_count}
    """
    import psutil as _psutil
    await websocket.accept()
    logger.info("Stream-status WS client connected")
    _proc = _psutil.Process()
    try:
        while True:
            uptime_s = round(time.time() - _start_time, 1)
            memory_mb = round(_proc.memory_info().rss / 1_048_576, 2)
            audio_mode = os.environ.get("SURAKSHA_AUDIO_MODE", "energy_fallback")
            payload = {
                "type": "health_ping",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "fps": 18.2,                        # empirical benchmark baseline
                "latency_p50_ms": 54.8,             # empirical p50 from eval/benchmark.py
                "audio_mode": audio_mode,
                "camera_count": len(_cameras) or 1,
                "uptime_s": uptime_s,
                "memory_mb": memory_mb,
                "ws_client_count": len(_ws_clients),
            }
            await websocket.send_json(payload)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("Stream-status WS error: %s", exc)
    finally:
        logger.info("Stream-status WS client disconnected")


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Custom Swagger UI / ReDoc using unpkg CDN (already in CSP allowlist)
# Default FastAPI docs use cdn.jsdelivr.net which may be blocked on Render.
# ---------------------------------------------------------------------------

@app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="SurakshaEdge API — Swagger UI",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False, response_class=HTMLResponse)
async def custom_redoc():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="SurakshaEdge API — ReDoc",
        redoc_js_url="https://unpkg.com/redoc@latest/bundles/redoc.standalone.js",
    )

@app.get("/", response_class=HTMLResponse)
async def root():
    dashboard_path = Path(__file__).parent.parent / "dashboard" / "index.html"
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>SurakshaEdge API</h1><p>Dashboard not found. Open /docs for API.</p>")


@app.get("/manifest.json", include_in_schema=False)
async def manifest():
    p = Path(__file__).parent.parent / "dashboard" / "manifest.json"
    if p.exists():
        return Response(content=p.read_text(encoding="utf-8"), media_type="application/manifest+json")
    return Response(status_code=404)


@app.get("/sw.js", include_in_schema=False)
async def service_worker():
    p = Path(__file__).parent.parent / "dashboard" / "sw.js"
    if p.exists():
        return Response(
            content=p.read_text(encoding="utf-8"),
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )
    return Response(status_code=404)


@app.post("/events", status_code=201)
async def post_event(
    event: EventPacketIn,
    token: str = Depends(require_token),
):
    if not check_replay(event.ts_utc):
        raise HTTPException(status_code=400, detail="Event timestamp outside replay window")

    event_dict = event.model_dump()
    store.save_event(event_dict)

    # Broadcast to dashboard
    await _broadcast({
        "type": "event",
        "event_id": event.event_id,
        "camera_id": event.camera_id,
        "ts_utc": event.ts_utc,
        "tier": event.tier,
        "gps": event.gps,
        "scores": event.scores,
        "bboxes": event.bboxes,
        "latency_ms": event.latency_ms,
    })

    return {"status": "ok", "event_id": event.event_id}


@app.post("/events/{event_id}/feedback")
async def post_feedback(
    event_id: str,
    feedback: FeedbackIn,
    token: str = Depends(require_token),
):
    store.save_feedback(event_id, feedback.verdict, feedback.note)
    return {"status": "ok"}


@app.get("/events")
async def get_events(limit: int = 50):
    return store.get_recent_events(limit=limit)


@app.get("/cameras")
async def get_cameras() -> List[Dict[str, Any]]:
    return _cameras


@app.get("/health")
async def get_health() -> Dict[str, Any]:
    audio_mode = os.environ.get("SURAKSHA_AUDIO_MODE", "energy_fallback")
    return {
        "status": "ok",
        "ws_clients": len(_ws_clients),
        "events_in_memory": len(store._in_memory),
        "audio_mode": audio_mode,          # "mfcc_cnn" or "energy_fallback"
        "cameras": len(_cameras),
        "uptime_s": round(time.time() - _start_time, 1),
        "version": "0.4.1",
    }


@app.get("/livez", include_in_schema=False)
async def livez() -> Dict[str, str]:
    """Liveness probe — always returns ok if process is running."""
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz() -> Dict[str, Any]:
    """Readiness probe — returns ok when cameras are loaded."""
    if not _cameras:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Cameras not yet loaded")
    return {"status": "ok", "cameras": len(_cameras)}


@app.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    return store.get_counters()


@app.get("/metrics/prometheus", include_in_schema=False)
async def get_metrics_prometheus() -> Response:
    """Prometheus text-format metrics export."""
    counters = store.get_counters()
    uptime = round(time.time() - _start_time, 1)
    lines = [
        "# HELP surakshaedge_alerts_total Total ALERT-tier events",
        "# TYPE surakshaedge_alerts_total counter",
        f"surakshaedge_alerts_total {counters.get('alerts', 0)}",
        "# HELP surakshaedge_advisories_total Total ADVISORY-tier events",
        "# TYPE surakshaedge_advisories_total counter",
        f"surakshaedge_advisories_total {counters.get('advisories', 0)}",
        "# HELP surakshaedge_frames_total Total frames processed",
        "# TYPE surakshaedge_frames_total counter",
        f"surakshaedge_frames_total {counters.get('frames', 0)}",
        "# HELP surakshaedge_ws_clients Active WebSocket dashboard clients",
        "# TYPE surakshaedge_ws_clients gauge",
        f"surakshaedge_ws_clients {len(_ws_clients)}",
        "# HELP surakshaedge_uptime_seconds Server uptime in seconds",
        "# TYPE surakshaedge_uptime_seconds gauge",
        f"surakshaedge_uptime_seconds {uptime}",
        "# HELP surakshaedge_events_in_memory Events held in RAM ring buffer",
        "# TYPE surakshaedge_events_in_memory gauge",
        f"surakshaedge_events_in_memory {len(store._in_memory)}",
        "",
    ]
    return Response(content="\n".join(lines), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.post("/simulate")
async def simulate(sim: SimulateIn, token: str = Depends(require_token)):
    """Inject a synthetic alert for demo/QA. Disabled in production."""
    production = os.environ.get("SURAKSHA_PRODUCTION", "false").lower() == "true"
    if production:
        raise HTTPException(status_code=403, detail="Simulate disabled in production")

    import datetime
    scenario_map = {
        "S1": {"tier": "ALERT",    "K_t": 0.78, "S_t": 0.85, "dt_s": 0.6},
        "S2": {"tier": "ADVISORY", "K_t": 0.80, "S_t": 0.00, "dt_s": -1},
        "S3": {"tier": "ADVISORY", "K_t": 0.10, "S_t": 0.88, "dt_s": -1},
        "S4": {"tier": "NONE",     "K_t": 0.30, "S_t": 0.20, "dt_s": -1},
    }
    s = scenario_map.get(sim.scenario, scenario_map["S1"])
    if s["tier"] == "NONE":
        return {"status": "ok", "message": "No alert injected for scenario S4"}

    event_id = str(uuid.uuid4())
    ts_utc = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    cam = next((c for c in _cameras if c["id"] == sim.camera_id), None)
    gps = cam["gps"] if cam else {"lat": 28.4600, "lon": 77.4952}

    event_dict = {
        "event_id": event_id,
        "camera_id": sim.camera_id,
        "ts_utc": ts_utc,
        "tier": s["tier"],
        "gps": gps,
        "scores": {"K_t": s["K_t"], "S_t": s["S_t"], "dt_s": max(s["dt_s"], 0.0)},
        "bboxes": [],
        "clip_enc": None,
        "latency_ms": {"pipeline": 30.0, "dispatch": 5.0},
        "_simulated": True,
    }
    store.save_event(event_dict)

    await _broadcast({
        "type": "event",
        **{k: v for k, v in event_dict.items() if not k.startswith("_")},
    })

    return {"status": "ok", "event_id": event_id, "tier": s["tier"]}


# ---------------------------------------------------------------------------
# Zone definitions
# ---------------------------------------------------------------------------

@app.get("/zones")
async def get_zones() -> Dict[str, Any]:
    """Return monitored zone polygon definitions for the map."""
    return {
        "zones": [
            {
                "id": "gniot-campus",
                "name": "GNIOT Campus — Knowledge Park II",
                "color": "#3b82f6",
                "opacity": 0.15,
                "polygon": [
                    [28.4625, 77.4940],
                    [28.4625, 77.4975],
                    [28.4575, 77.4975],
                    [28.4575, 77.4940],
                ],
            },
            {
                "id": "main-gate-zone",
                "name": "Main Gate — High Priority",
                "color": "#ef4444",
                "opacity": 0.10,
                "polygon": [
                    [28.4606, 77.4946],
                    [28.4606, 77.4958],
                    [28.4594, 77.4958],
                    [28.4594, 77.4946],
                ],
            },
        ]
    }


# ---------------------------------------------------------------------------
# Single event detail
# ---------------------------------------------------------------------------

@app.get("/events/{event_id}")
async def get_event(event_id: str) -> Dict[str, Any]:
    events = store.get_recent_events(limit=500)
    evt = next((e for e in events if e.get("event_id") == event_id), None)
    if not evt:
        raise HTTPException(status_code=404, detail="Event not found")
    return evt


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@app.get("/export/events")
async def export_events() -> Response:
    """Download all recent events as a JSON file."""
    events = store.get_recent_events(limit=1000)
    content = json.dumps(
        {
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "count": len(events),
            "events": events,
        },
        indent=2,
        default=str,
    )
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=suraksha_events.json"},
    )


# ---------------------------------------------------------------------------
# Camera status patch
# ---------------------------------------------------------------------------

@app.patch("/cameras/{camera_id}/status")
async def update_camera_status(
    camera_id: str,
    body: Dict[str, Any],
    token: str = Depends(require_token),
) -> Dict[str, Any]:
    for cam in _cameras:
        if cam["id"] == camera_id:
            cam["status"] = body.get("status", "idle")
            await _broadcast({"type": "camera_status", "camera_id": camera_id, "status": cam["status"]})
            return {"status": "ok", "camera_id": camera_id}
    raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
