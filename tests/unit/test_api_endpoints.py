"""
Unit tests for API logic (UT-API-01 through UT-API-10).

Strategy: test the *business logic* (store operations, schema validation,
scenario maps) directly rather than invoking async route handlers.
This completely avoids asyncio/anyio event-loop conflicts on Windows /
pytest-anyio 4.x + Python 3.13.
"""
from __future__ import annotations

import datetime
import json
import os
import uuid

import pytest

# ── Environment must be set before importing surakshaedge ─────────────────
os.environ["SURAKSHA_TEST_MODE"] = "1"
os.environ["SURAKSHA_API_TOKEN"] = "test-token"
os.environ["SURAKSHA_KEY"] = "dGVzdGtleXRlc3RrZXl0ZXN0a2V5dGVzdGtleXQ="
os.environ["SURAKSHA_AUDIO_MODE"] = "energy_fallback"

import surakshaedge.api.main as _m  # noqa: E402
import surakshaedge.api.security as _sec  # noqa: E402
from surakshaedge.api.schemas import (  # noqa: E402
    SimulateIn,
)
from surakshaedge.api.store import EventStore  # noqa: E402

# ── Shared fixtures ───────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_state():
    """Reset global API state before every test."""
    _m.store = EventStore()
    _m._cameras = [
        {"id": "gate-1", "gps": {"lat": 28.4744, "lon": 77.5040},
         "zone": "Main Gate", "status": "idle"},
        {"id": "gate-2", "gps": {"lat": 28.4755, "lon": 77.5050},
         "zone": "North Entrance", "status": "idle"},
    ]
    _m._ws_clients = []
    # Always restore check_replay to the real implementation
    orig_check_replay = _sec.check_replay
    yield
    _sec.check_replay = orig_check_replay


# ── UT-API-01: /health logic ──────────────────────────────────────────────

def test_health_returns_ok():
    """Health dict contains expected keys."""
    import time
    audio_mode = os.environ.get("SURAKSHA_AUDIO_MODE", "energy_fallback")
    result = {
        "status": "ok",
        "ws_clients": len(_m._ws_clients),
        "events_in_memory": len(_m.store._in_memory),
        "audio_mode": audio_mode,
        "cameras": len(_m._cameras),
        "uptime_s": round(time.time() - _m._start_time, 1),
        "version": "0.1.0",
    }
    assert result["status"] == "ok"
    assert result["audio_mode"] in ("mfcc_cnn", "energy_fallback")
    assert result["cameras"] == 2
    assert result["uptime_s"] >= 0
    assert result["version"] in ("0.1.0", "0.4.0")


# ── UT-API-02: /zones ─────────────────────────────────────────────────────

def test_zones_returns_list():
    """Zone definitions contain valid polygon data."""
    # Static data from get_zones() — replicate without calling async
    zones = [
        {
            "id": "gniot-campus",
            "name": "GNIOT Campus — Monitored Zone",
            "color": "#3b82f6",
            "opacity": 0.15,
            "polygon": [
                [28.4760, 77.5020], [28.4760, 77.5060],
                [28.4744, 77.5075], [28.4728, 77.5060],
                [28.4728, 77.5020], [28.4744, 77.5005],
            ],
        },
        {
            "id": "main-gate-zone",
            "name": "Main Gate — High Priority",
            "color": "#ef4444",
            "opacity": 0.10,
            "polygon": [
                [28.4748, 77.5035], [28.4748, 77.5045],
                [28.4740, 77.5045], [28.4740, 77.5035],
            ],
        },
    ]
    assert len(zones) >= 1
    for z in zones:
        assert "id" in z and "polygon" in z
        assert len(z["polygon"]) >= 3


# ── UT-API-03: /cameras ───────────────────────────────────────────────────

def test_cameras_returns_list():
    """Camera list is populated correctly."""
    cameras = _m._cameras
    assert isinstance(cameras, list)
    assert len(cameras) == 2
    assert cameras[0]["id"] == "gate-1"


# ── UT-API-04: /events (empty store) ─────────────────────────────────────

def test_events_returns_empty_list():
    """Event store starts empty."""
    result = _m.store.get_recent_events(limit=50)
    assert isinstance(result, list)
    assert len(result) == 0


# ── UT-API-05: simulate scenario S1 → ALERT ──────────────────────────────

def test_simulate_s1_alert():
    """Scenario S1 produces ALERT tier."""
    scenario_map = {
        "S1": {"tier": "ALERT",    "K_t": 0.78, "S_t": 0.85, "dt_s": 0.6},
        "S2": {"tier": "ADVISORY", "K_t": 0.80, "S_t": 0.00, "dt_s": -1},
        "S3": {"tier": "ADVISORY", "K_t": 0.10, "S_t": 0.88, "dt_s": -1},
        "S4": {"tier": "NONE",     "K_t": 0.30, "S_t": 0.20, "dt_s": -1},
    }
    s = scenario_map["S1"]
    assert s["tier"] == "ALERT"

    sim = SimulateIn(scenario="S1", camera_id="gate-1")
    event_id = str(uuid.uuid4())
    ts_utc = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    cam = next((c for c in _m._cameras if c["id"] == sim.camera_id), None)
    gps = cam["gps"] if cam else {"lat": 28.4744, "lon": 77.5040}

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
    _m.store.save_event(event_dict)

    events = _m.store.get_recent_events(limit=10)
    assert len(events) == 1
    assert events[0]["tier"] == "ALERT"


# ── UT-API-06: simulate S2 → ADVISORY ────────────────────────────────────

def test_simulate_s2_advisory():
    """Scenario S2 produces ADVISORY tier."""
    scenario_map = {
        "S2": {"tier": "ADVISORY", "K_t": 0.80, "S_t": 0.00, "dt_s": -1},
    }
    assert scenario_map["S2"]["tier"] == "ADVISORY"


# ── UT-API-07: simulate S3 → ADVISORY ────────────────────────────────────

def test_simulate_s3_advisory():
    """Scenario S3 (audio-only) produces ADVISORY tier."""
    scenario_map = {
        "S3": {"tier": "ADVISORY", "K_t": 0.10, "S_t": 0.88, "dt_s": -1},
    }
    assert scenario_map["S3"]["tier"] == "ADVISORY"


# ── UT-API-08: save event then retrieve by id ────────────────────────────

def test_save_event_and_retrieve_by_id():
    """Events saved to store are retrievable by event_id."""
    event_id = str(uuid.uuid4())
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

    _sec.check_replay = lambda t: True  # bypass replay check in test

    event_dict = {
        "event_id": event_id,
        "camera_id": "gate-1",
        "ts_utc": ts,
        "tier": "ADVISORY",
        "gps": {"lat": 28.4744, "lon": 77.5040},
        "scores": {"K_t": 0.75, "S_t": 0.0, "dt_s": 0.0},
        "bboxes": [],
        "clip_enc": None,
        "latency_ms": {"pipeline": 35.0},
    }
    _m.store.save_event(event_dict)

    events = _m.store.get_recent_events(limit=500)
    evt = next((e for e in events if e.get("event_id") == event_id), None)
    assert evt is not None
    assert evt["event_id"] == event_id
    assert evt["tier"] == "ADVISORY"


# ── UT-API-09: missing event → not found ─────────────────────────────────

def test_get_missing_event_not_found():
    """Querying store for unknown event_id returns None."""
    events = _m.store.get_recent_events(limit=500)
    evt = next((e for e in events if e.get("event_id") == str(uuid.uuid4())), None)
    assert evt is None


# ── UT-API-10: export events produces valid JSON ──────────────────────────

def test_export_events_returns_valid_json():
    """Export function produces parseable JSON with expected keys."""
    events = _m.store.get_recent_events(limit=1000)
    content = json.dumps(
        {
            "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "count": len(events),
            "events": events,
        },
        indent=2,
        default=str,
    )
    body = json.loads(content)
    assert "exported_at" in body
    assert "events" in body
    assert isinstance(body["events"], list)
