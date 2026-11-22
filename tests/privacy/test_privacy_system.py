"""
Privacy system tests (PT-01 to PT-06).
Run: pytest tests/privacy/ -v

PT-01 fast mode (CI): watches for 10 seconds (env SURAKSHA_PRIVACY_SOAK=600 for full 10-min run).
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from surakshaedge.edge.privacy import PrivacyManager, decrypt_payload, encrypt_payload

# ---------------------------------------------------------------------------
# PT-01: No image/video files written during sustained no-alert operation
# ---------------------------------------------------------------------------

def _watch_for_media_files(watch_dirs, found_files, stop_event):
    """Background thread: record any new .jpg/.mp4/.avi/.png files."""
    known = set()
    for d in watch_dirs:
        for ext in ("*.jpg", "*.mp4", "*.avi", "*.png", "*.jpeg"):
            known.update(Path(d).rglob(ext))
    while not stop_event.is_set():
        for d in watch_dirs:
            for ext in ("*.jpg", "*.mp4", "*.avi", "*.png", "*.jpeg"):
                for f in Path(d).rglob(ext):
                    if f not in known:
                        found_files.append(str(f))
        time.sleep(0.5)


def test_pt01_no_media_files_written_sustained(tmp_path):
    """
    PT-01: Run the privacy manager continuously for SOAK seconds pushing frames.
    Assert no image or video file is written to disk at any point.

    Default: 10 s (fast CI mode).
    Full test: set env var SURAKSHA_PRIVACY_SOAK=600 for 10 minutes.
    """
    soak_s = int(os.environ.get("SURAKSHA_PRIVACY_SOAK", "10"))
    pm = PrivacyManager(buffer_s=5.0, retention_hours=1.0, audit_log_path=None)

    found_files = []
    stop_event = threading.Event()

    # Watch tmp_path, working dir, and results/
    watch_dirs = [tmp_path, Path("."), Path("results")] 
    watch_dirs = [d for d in watch_dirs if d.exists()]

    watcher = threading.Thread(
        target=_watch_for_media_files,
        args=(watch_dirs, found_files, stop_event),
        daemon=True,
    )
    watcher.start()

    # Push synthetic frames for soak_s seconds (no alert triggered)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    t_end = time.monotonic() + soak_s
    frame_count = 0
    while time.monotonic() < t_end:
        pm.push_frame(frame, time.monotonic_ns())
        frame_count += 1
        time.sleep(0.033)  # ~30 FPS

    stop_event.set()
    watcher.join(timeout=2.0)

    assert len(found_files) == 0, (
        f"PT-01 FAILED: media files written during {soak_s}s no-alert run: {found_files}"
    )
    print(f"\nPT-01 PASSED: {frame_count} frames pushed over {soak_s}s, 0 media files written.")
    print("  → For full 10-min test: SURAKSHA_PRIVACY_SOAK=600 pytest tests/privacy/ -v -s")


# PT-03: On alert, only an encrypted blob is produced (no plain media)
def test_pt03_alert_produces_encrypted_blob_only():
    pm = PrivacyManager(buffer_s=2.0, retention_hours=1.0, audit_log_path=None)
    for i in range(10):
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        pm.push_frame(img, time.monotonic_ns())

    packet = pm.build_event_packet(
        camera_id="gate-1", tier="ALERT",
        gps={"lat": 28.0, "lon": 77.0},
        K_t=0.8, S_t=0.9, dt_s=0.5,
        bboxes=[], pipeline_ms=30.0, dispatch_ms=5.0,
    )
    # clip_enc should exist and be a dict with nonce + ciphertext
    assert packet.clip_enc is not None, "clip_enc should be set on ALERT"
    assert "nonce" in packet.clip_enc
    assert "ciphertext" in packet.clip_enc
    # It should be decryptable
    dec = decrypt_payload(packet.clip_enc, packet.event_id.encode())
    assert len(dec) > 0


# PT-04: Decryption with wrong key / tampered data fails
def test_pt04_tamper_detection():
    import base64
    data = b"secure payload"
    enc = encrypt_payload(data, b"event-id")
    ct = bytearray(base64.b64decode(enc["ciphertext"]))
    ct[10] ^= 0xFF
    enc["ciphertext"] = base64.b64encode(bytes(ct)).decode()
    with pytest.raises(Exception):
        decrypt_payload(enc, b"event-id")


# PT-05: Retention — old events are purged
def test_pt05_retention_purge():
    """After setting retention to 0h and calling purge, DB should be empty."""
    import sqlite3
    import tempfile
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from surakshaedge.api.store import EventStore
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    store = EventStore(db_path=db, retention_hours=0.0)
    store.save_event({
        "event_id": "test-1", "camera_id": "gate-1", "ts_utc": "2026-10-25T00:00:00Z",
        "tier": "ALERT", "gps": {}, "scores": {}, "bboxes": [], "latency_ms": {},
    })
    store.purge_old()
    # Explicitly close all connections before checking
    del store
    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()
    # Try cleanup — ignore if locked on Windows
    try:
        os.unlink(db)
    except PermissionError:
        pass
    assert count == 0, f"Expected 0 events after purge, got {count}"


# PT-06: Audit log contains no media
def test_pt06_audit_log_no_media(tmp_path):
    import json
    log_path = str(tmp_path / "audit.jsonl")
    pm = PrivacyManager(buffer_s=2.0, retention_hours=1.0, audit_log_path=log_path)
    for _ in range(5):
        pm.push_frame(np.zeros((480, 640, 3), dtype=np.uint8), time.monotonic_ns())
    pm.build_event_packet("gate-1", "ALERT", {"lat": 0, "lon": 0},
                          0.8, 0.9, 0.5, [], 30.0, 5.0)
    with open(log_path) as f:
        for line in f:
            entry = json.loads(line)
            # Should only have metadata, no media bytes
            assert "ciphertext" not in str(entry)
            assert "nonce" not in str(entry)
            assert "event_id" in entry
            assert "tier" in entry
