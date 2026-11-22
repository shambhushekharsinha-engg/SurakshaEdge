"""
Unit tests for the fusion gate (UT-09) - truth table.
Cases A–I per the PRD/Test Plan.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from surakshaedge.edge.fusion import FusionGate


def gate() -> FusionGate:
    return FusionGate(gate_s=1.5, cooldown_s=10.0)


def ts(seconds: float) -> int:
    return int(seconds * 1e9)


# Case A: K at t=10.0, S at t=10.6 → ALERT (dt=0.6s)
def test_case_A():
    g = gate()
    # K flag rises at t=10.0
    d = g.update(True, False, 0.8, 0.1, ts(10.0))
    assert d.tier == "NONE"
    # S flag rises at t=10.6
    d = g.update(True, True, 0.8, 0.85, ts(10.6))
    assert d.tier == "ALERT", f"Case A: expected ALERT, got {d.tier}"


# Case B: boundary — dt = exactly 1.5s → ALERT
def test_case_B():
    g = gate()
    g.update(True, False, 0.8, 0.1, ts(10.0))
    d = g.update(True, True, 0.8, 0.85, ts(11.5))
    assert d.tier == "ALERT", f"Case B: expected ALERT at boundary, got {d.tier}"


# Case C: dt = 1.6s → No ALERT (gap above 1.5s)
def test_case_C():
    g = gate()
    g.update(True, False, 0.8, 0.1, ts(10.0))
    # At t=11.6, K flag has expired (> 1.5s old)
    d = g.update(False, True, 0.1, 0.85, ts(11.6))
    assert d.tier != "ALERT", f"Case C: expected no ALERT, got {d.tier}"


# Case D: audio first, then video within 1.5s → ALERT
def test_case_D():
    g = gate()
    g.update(False, True, 0.1, 0.85, ts(10.0))
    d = g.update(True, True, 0.8, 0.85, ts(10.9))
    assert d.tier == "ALERT", f"Case D: audio-first ALERT, got {d.tier}"


# Case E: vision only, K ≥ 0.75 sustained 1s → ADVISORY somewhere in the run
def test_case_E():
    g = gate()
    decisions = []
    for i in range(15):
        d = g.update(False, False, 0.80, 0.0, ts(10.0 + i * 0.1))
        decisions.append(d.tier)
    assert "ADVISORY" in decisions, f"Case E: expected ADVISORY (vision-only) in decisions, got {decisions}"


# Case F: audio only, S ≥ 0.85 sustained 0.5s → ADVISORY somewhere in the run
def test_case_F():
    g = gate()
    decisions = []
    for i in range(10):
        d = g.update(False, False, 0.0, 0.90, ts(10.0 + i * 0.1))
        decisions.append(d.tier)
    assert "ADVISORY" in decisions, f"Case F: expected ADVISORY (audio-only) in decisions, got {decisions}"


# Case G: ALERT then another pair within 10s → suppressed by cooldown
def test_case_G():
    g = gate()
    g.update(True, False, 0.8, 0.1, ts(10.0))
    d1 = g.update(True, True, 0.8, 0.85, ts(10.6))
    assert d1.tier == "ALERT"
    # Second pair within cooldown (5s later)
    g._t_k = None; g._t_s = None  # reset flags for next gate check
    g.update(True, False, 0.8, 0.1, ts(15.0))
    d2 = g.update(True, True, 0.8, 0.85, ts(15.5))
    assert d2.tier != "ALERT" or d2.reason == "Escalation during cooldown", \
        f"Case G: expected suppression in cooldown, got {d2.tier}"


# Case H: ALERT fires, then score rises by ≥0.15 during cooldown → escalation event
def test_case_H():
    g = gate()
    # First ALERT fires
    g.update(True, False, 0.70, 0.1, ts(10.0))
    d1 = g.update(True, True, 0.70, 0.85, ts(10.6))
    assert d1.tier == "ALERT", f"Case H setup: expected ALERT, got {d1.tier}"
    assert d1.K_t == pytest.approx(0.70, abs=0.01)

    # During 10s cooldown, score rises by ≥0.15 → escalation
    # Reset internal flag timestamps to simulate new detection arriving
    g._t_k = ts(12.0) / 1e9
    g._t_s = ts(12.0) / 1e9
    d2 = g.update(True, True, 0.90, 0.95, ts(12.5))   # K rose 0.20, S rose 0.10 → escalates
    assert d2.tier == "ALERT", f"Case H: expected escalation ALERT, got {d2.tier}"
    assert "scalat" in d2.reason.lower(), f"Case H: reason should mention escalation: {d2.reason}"


# Case I: both flags drop before pair completes → No alert
def test_case_I():
    g = gate()
    g.update(True, False, 0.8, 0.1, ts(10.0))
    # K flag drops, S never rises
    d = g.update(False, False, 0.1, 0.1, ts(10.5))
    assert d.tier == "NONE", f"Case I: expected NONE, got {d.tier}"
