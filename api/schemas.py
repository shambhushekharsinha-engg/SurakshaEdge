"""
SurakshaEdge - Pydantic schemas for API (with strict validation)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

VALID_TIERS = {"ALERT", "ADVISORY"}


class EncryptedClip(BaseModel):
    nonce: str
    ciphertext: str


class EventPacketIn(BaseModel):
    event_id: str = Field(..., min_length=4, max_length=64)
    camera_id: str = Field(..., min_length=1, max_length=64)
    ts_utc: str
    tier: str
    gps: Dict[str, float]
    scores: Dict[str, float] = Field(default_factory=dict)
    bboxes: List[List[float]] = Field(default_factory=list)
    clip_enc: Optional[EncryptedClip] = None
    latency_ms: Dict[str, float] = Field(default_factory=dict)

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        if v not in VALID_TIERS:
            raise ValueError(f"tier must be one of {VALID_TIERS}, got '{v}'")
        return v

    @field_validator("gps")
    @classmethod
    def validate_gps(cls, v: Dict[str, float]) -> Dict[str, float]:
        lat = v.get("lat")
        lon = v.get("lon")
        if lat is None or lon is None:
            raise ValueError("gps must contain 'lat' and 'lon' keys")
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"GPS lat {lat} out of range [-90, 90]")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"GPS lon {lon} out of range [-180, 180]")
        return v

    @field_validator("scores")
    @classmethod
    def validate_scores(cls, v: Dict[str, float]) -> Dict[str, float]:
        clampable = {"K_t", "S_t", "Q_p"}
        for key in clampable:
            if key in v:
                v[key] = max(0.0, min(1.0, float(v[key])))
        return v

    @field_validator("ts_utc")
    @classmethod
    def validate_ts_utc(cls, v: str) -> str:
        import datetime
        try:
            datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError(f"ts_utc '{v}' is not a valid ISO-8601 timestamp")
        return v


class FeedbackIn(BaseModel):
    verdict: str
    note: Optional[str] = Field(default=None, max_length=500)

    @field_validator("verdict")
    @classmethod
    def validate_verdict(cls, v: str) -> str:
        valid = {"true_alarm", "false_alarm", "uncertain"}
        if v not in valid:
            raise ValueError(f"verdict must be one of {valid}")
        return v


class SimulateIn(BaseModel):
    scenario: str = Field(..., pattern=r"^S[1-4]$")
    camera_id: str = Field(default="gate-1", min_length=1, max_length=64)


class CameraOut(BaseModel):
    id: str
    gps: Dict[str, float]
    zone: str


class HealthOut(BaseModel):
    status: str
    ws_clients: int
    events_in_memory: int
    audio_mode: str
    cameras: int
    uptime_s: float
    version: str


class MetricsOut(BaseModel):
    frames: int
    drops: int
    alerts: int
    advisories: int
    stage_latency: Dict[str, Any] = Field(default_factory=dict)
