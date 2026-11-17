"""
SurakshaEdge - Pydantic schemas for API
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import time


class EncryptedClip(BaseModel):
    nonce: str
    ciphertext: str


class EventPacketIn(BaseModel):
    event_id: str
    camera_id: str
    ts_utc: str
    tier: str   # ALERT | ADVISORY
    gps: Dict[str, float]
    scores: Dict[str, float]
    bboxes: List[List[float]] = Field(default_factory=list)
    clip_enc: Optional[EncryptedClip] = None
    latency_ms: Dict[str, float] = Field(default_factory=dict)


class FeedbackIn(BaseModel):
    verdict: str   # "true_alarm" | "false_alarm"
    note: Optional[str] = None


class SimulateIn(BaseModel):
    scenario: str   # "S1" | "S2" | "S3" | "S4"
    camera_id: str = "gate-1"


class CameraOut(BaseModel):
    id: str
    gps: Dict[str, float]
    zone: str


class HealthOut(BaseModel):
    status: str
    ingest: str
    models: str
    queue_depth: int


class MetricsOut(BaseModel):
    frames: int
    drops: int
    alerts: int
    advisories: int
    stage_latency: Dict[str, Any] = Field(default_factory=dict)
