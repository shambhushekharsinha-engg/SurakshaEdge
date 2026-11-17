"""
SurakshaEdge - Temporal fusion gate
Raises ALERT when K_flag and S_flag both fire within gate_s (1.5 s).
Raises ADVISORY for vision-only or audio-only triggers.
Implements cooldown and escalation logic.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

GATE_S = 1.5
COOLDOWN_S = 10.0
ESCALATION_DELTA = 0.15

# Vision-only advisory thresholds
ADVISORY_K_THRESHOLD = 0.75
ADVISORY_K_SUSTAIN_S = 1.0

# Audio-only advisory thresholds
ADVISORY_S_THRESHOLD = 0.85
ADVISORY_S_SUSTAIN_S = 0.5


@dataclass
class Decision:
    tier: str           # "ALERT" | "ADVISORY" | "NONE"
    ts_ns: int
    K_t: float
    S_t: float
    dt_s: float         # time gap between K_flag and S_flag (or -1 if N/A)
    reason: str = ""    # human-readable trigger description
    track_ids: list = field(default_factory=list)


class FusionGate:
    """
    Deterministic temporal gate per camera zone.
    Call update() on every frame with the latest kinematic and audio scores.
    """

    def __init__(
        self,
        gate_s: float = GATE_S,
        cooldown_s: float = COOLDOWN_S,
        escalation_delta: float = ESCALATION_DELTA,
    ):
        self.gate_s = gate_s
        self.cooldown_s = cooldown_s
        self.escalation_delta = escalation_delta

        self._t_k: Optional[float] = None   # wall seconds (monotonic)
        self._t_s: Optional[float] = None
        self._k_t_at_flag: float = 0.0
        self._s_t_at_flag: float = 0.0

        self._cooldown_until: float = 0.0
        self._last_alert_k: float = 0.0
        self._last_alert_s: float = 0.0

        # Advisory persistence trackers
        self._k_advisory_start: Optional[float] = None
        self._s_advisory_start: Optional[float] = None

    def update(
        self,
        k_flag: bool,
        s_flag: bool,
        K_t: float,
        S_t: float,
        ts_ns: int,
        track_ids: Optional[list] = None,
    ) -> Decision:
        now = ts_ns / 1e9  # seconds

        # Update flag timestamps
        if k_flag:
            if self._t_k is None:
                self._t_k = now
                self._k_t_at_flag = K_t
        else:
            self._t_k = None

        if s_flag:
            if self._t_s is None:
                self._t_s = now
                self._s_t_at_flag = S_t
        else:
            self._t_s = None

        # Expire stale flags
        if self._t_k is not None and (now - self._t_k) > self.gate_s:
            self._t_k = None
        if self._t_s is not None and (now - self._t_s) > self.gate_s:
            self._t_s = None

        in_cooldown = now < self._cooldown_until

        # -----------------------------------------------------------
        # Full ALERT: both flags set within gate window
        # -----------------------------------------------------------
        if self._t_k is not None and self._t_s is not None:
            dt_s = abs(self._t_k - self._t_s)
            if not in_cooldown:
                self._cooldown_until = now + self.cooldown_s
                self._last_alert_k = K_t
                self._last_alert_s = S_t
                self._t_k = None
                self._t_s = None
                logger.info("ALERT fired: K_t=%.2f S_t=%.2f dt=%.2fs", K_t, S_t, dt_s)
                return Decision(
                    tier="ALERT", ts_ns=ts_ns, K_t=K_t, S_t=S_t, dt_s=dt_s,
                    reason=f"Vision+Audio gate: K={K_t:.2f} S={S_t:.2f} dt={dt_s:.2f}s",
                    track_ids=track_ids or [],
                )
            else:
                # Escalation check
                k_rise = K_t - self._last_alert_k
                s_rise = S_t - self._last_alert_s
                if k_rise >= self.escalation_delta or s_rise >= self.escalation_delta:
                    self._cooldown_until = now + self.cooldown_s
                    self._last_alert_k = K_t
                    self._last_alert_s = S_t
                    logger.info("ALERT escalated: K_t=%.2f S_t=%.2f", K_t, S_t)
                    return Decision(
                        tier="ALERT", ts_ns=ts_ns, K_t=K_t, S_t=S_t, dt_s=dt_s,
                        reason="Escalation during cooldown",
                        track_ids=track_ids or [],
                    )

        # -----------------------------------------------------------
        # ADVISORY: vision-only
        # -----------------------------------------------------------
        if K_t >= ADVISORY_K_THRESHOLD:
            if self._k_advisory_start is None:
                self._k_advisory_start = now
            elif (now - self._k_advisory_start) >= ADVISORY_K_SUSTAIN_S and not in_cooldown:
                logger.info("ADVISORY (vision-only): K_t=%.2f", K_t)
                self._k_advisory_start = None
                return Decision(
                    tier="ADVISORY", ts_ns=ts_ns, K_t=K_t, S_t=S_t, dt_s=-1,
                    reason=f"Vision-only: K_t={K_t:.2f} sustained {ADVISORY_K_SUSTAIN_S}s",
                    track_ids=track_ids or [],
                )
        else:
            self._k_advisory_start = None

        # -----------------------------------------------------------
        # ADVISORY: audio-only
        # -----------------------------------------------------------
        if S_t >= ADVISORY_S_THRESHOLD:
            if self._s_advisory_start is None:
                self._s_advisory_start = now
            elif (now - self._s_advisory_start) >= ADVISORY_S_SUSTAIN_S and not in_cooldown:
                logger.info("ADVISORY (audio-only): S_t=%.2f", S_t)
                self._s_advisory_start = None
                return Decision(
                    tier="ADVISORY", ts_ns=ts_ns, K_t=K_t, S_t=S_t, dt_s=-1,
                    reason=f"Audio-only: S_t={S_t:.2f} sustained {ADVISORY_S_SUSTAIN_S}s",
                    track_ids=track_ids or [],
                )
        else:
            self._s_advisory_start = None

        return Decision(tier="NONE", ts_ns=ts_ns, K_t=K_t, S_t=S_t, dt_s=-1)
