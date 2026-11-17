"""
SurakshaEdge - Event store (SQLite + in-memory)
All SQLite connections are explicitly closed to avoid ResourceWarning on Python 3.13.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("SURAKSHA_DB", "results/events.db")


class EventStore:
    def __init__(self, db_path: str = DB_PATH, retention_hours: float = 24.0):
        self.db_path = db_path
        self.retention_hours = retention_hours
        self._lock = threading.Lock()
        self._in_memory: List[Dict[str, Any]] = []
        self._counters = {"frames": 0, "drops": 0, "alerts": 0, "advisories": 0}
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._connect()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    camera_id TEXT,
                    ts_utc TEXT,
                    tier TEXT,
                    gps TEXT,
                    scores TEXT,
                    bboxes TEXT,
                    clip_enc TEXT,
                    latency_ms TEXT,
                    created_at REAL,
                    feedback TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()
        logger.info("EventStore DB initialised: %s", self.db_path)

    def save_event(self, event: Dict[str, Any]):
        with self._lock:
            self._in_memory.append(event)
            if len(self._in_memory) > 500:
                self._in_memory = self._in_memory[-500:]
            conn = self._connect()
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO events
                    (event_id, camera_id, ts_utc, tier, gps, scores, bboxes, clip_enc, latency_ms, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event["event_id"],
                    event["camera_id"],
                    event["ts_utc"],
                    event["tier"],
                    json.dumps(event.get("gps", {})),
                    json.dumps(event.get("scores", {})),
                    json.dumps(event.get("bboxes", [])),
                    json.dumps(event.get("clip_enc")) if event.get("clip_enc") else None,
                    json.dumps(event.get("latency_ms", {})),
                    time.time(),
                ))
                conn.commit()
            except Exception as e:
                logger.error("DB save failed: %s", e)
            finally:
                conn.close()

            tier = event.get("tier", "")
            if tier == "ALERT":
                self._counters["alerts"] += 1
            elif tier == "ADVISORY":
                self._counters["advisories"] += 1

    def save_feedback(self, event_id: str, verdict: str, note: Optional[str] = None):
        feedback = json.dumps({"verdict": verdict, "note": note})
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("UPDATE events SET feedback=? WHERE event_id=?", (feedback, event_id))
                conn.commit()
            except Exception as e:
                logger.error("Feedback save failed: %s", e)
            finally:
                conn.close()

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self._in_memory[-limit:]))

    def get_counters(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._counters)

    def purge_old(self):
        """Delete events older than retention_hours."""
        cutoff = time.time() - self.retention_hours * 3600
        with self._lock:
            conn = self._connect()
            try:
                conn.execute("DELETE FROM events WHERE created_at < ?", (cutoff,))
                conn.commit()
            except Exception as e:
                logger.error("Purge failed: %s", e)
            finally:
                conn.close()
            self._in_memory = [e for e in self._in_memory
                               if e.get("created_at", time.time()) > cutoff]
