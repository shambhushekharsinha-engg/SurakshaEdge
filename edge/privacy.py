"""
SurakshaEdge - Privacy and security module
RAM ring buffer, AES-256-GCM encryption, audit log, retention purge.
"""
from __future__ import annotations

import base64
import collections
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

_AES_KEY_ENV = "SURAKSHA_KEY"


def _get_key() -> bytes:
    """Load AES-256 key from env (base64-encoded 32 bytes)."""
    raw = os.environ.get(_AES_KEY_ENV, "")
    if raw:
        try:
            key = base64.b64decode(raw)
            if len(key) == 32:
                return key
        except Exception:
            pass
    logger.warning("SURAKSHA_KEY not set – using insecure demo key.")
    return b"surakshaedge-demo-key-000000000a"   # exactly 32 bytes


def encrypt_payload(data: bytes, associated_data: bytes = b"") -> Dict[str, str]:
    """AES-256-GCM encrypt. Returns dict with nonce and ciphertext (base64)."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = _get_key()
    nonce = os.urandom(12)          # 96-bit random nonce
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, data, associated_data or None)
    return {
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ct).decode(),
    }


def decrypt_payload(enc: Dict[str, str], associated_data: bytes = b"") -> bytes:
    """AES-256-GCM decrypt. Raises on tag mismatch."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = _get_key()
    nonce = base64.b64decode(enc["nonce"])
    ct    = base64.b64decode(enc["ciphertext"])
    return AESGCM(key).decrypt(nonce, ct, associated_data or None)


@dataclass
class EventPacket:
    event_id: str
    camera_id: str
    ts_utc: str
    tier: str
    gps: Dict[str, float]
    scores: Dict[str, float]
    bboxes: List[List[float]]
    clip_enc: Optional[Dict[str, str]]
    latency_ms: Dict[str, float]
    retention_hours: float = 24.0
    created_at: float = field(default_factory=time.time)


class RingBuffer:
    """RAM-only ring buffer for the last N frames (JPEG-compressed)."""

    def __init__(self, max_frames: int = 125, jpeg_quality: int = 70):
        self.max_frames = max_frames
        self.jpeg_quality = jpeg_quality
        self._buf: collections.deque = collections.deque(maxlen=max_frames)

    def push(self, img: np.ndarray, ts_ns: int):
        import cv2
        ret, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
        if ret:
            self._buf.append((ts_ns, bytes(enc)))

    def snapshot(self) -> List[Tuple[int, bytes]]:
        return list(self._buf)

    def clear(self):
        self._buf.clear()


class PrivacyManager:
    """Manages ring buffer, encryption of clips, audit log and retention."""

    def __init__(
        self,
        buffer_s: float = 5.0,
        retention_hours: float = 24.0,
        fps_estimate: float = 25.0,
        audit_log_path: Optional[str] = None,
    ):
        max_frames = int(buffer_s * fps_estimate)
        self._ring = RingBuffer(max_frames=max_frames)
        self.retention_hours = retention_hours
        self._audit: List[Dict[str, Any]] = []
        self._audit_path = audit_log_path
        if audit_log_path:
            os.makedirs(os.path.dirname(audit_log_path) if os.path.dirname(audit_log_path) else ".", exist_ok=True)

    def push_frame(self, img: np.ndarray, ts_ns: int):
        self._ring.push(img, ts_ns)

    def build_event_packet(
        self,
        camera_id: str,
        tier: str,
        gps: Dict[str, float],
        K_t: float,
        S_t: float,
        dt_s: float,
        bboxes: List[List[float]],
        pipeline_ms: float,
        dispatch_ms: float,
    ) -> EventPacket:
        import datetime
        event_id = str(uuid.uuid4())
        ts_utc = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

        frames = self._ring.snapshot()
        if frames:
            clip_bytes = b"".join(jpg for _, jpg in frames)
            clip_enc = encrypt_payload(clip_bytes, event_id.encode())
        else:
            clip_enc = None

        packet = EventPacket(
            event_id=event_id,
            camera_id=camera_id,
            ts_utc=ts_utc,
            tier=tier,
            gps=gps,
            scores={"K_t": round(K_t, 4), "S_t": round(S_t, 4), "dt_s": round(dt_s, 3)},
            bboxes=bboxes,
            clip_enc=clip_enc,
            latency_ms={"pipeline": round(pipeline_ms, 2), "dispatch": round(dispatch_ms, 2)},
            retention_hours=self.retention_hours,
        )
        self._log_audit(event_id, tier, K_t, S_t)
        return packet

    def _log_audit(self, event_id: str, tier: str, K_t: float, S_t: float):
        import datetime
        entry = {
            "event_id": event_id,
            "time": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "tier": tier,
            "K_t": round(K_t, 4),
            "S_t": round(S_t, 4),
        }
        self._audit.append(entry)
        if self._audit_path:
            with open(self._audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        logger.info("AUDIT: %s", json.dumps(entry))
