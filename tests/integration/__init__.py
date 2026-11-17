"""
SurakshaEdge - Integration tests
Replay test scenarios through the pipeline end-to-end.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from surakshaedge.edge.kinematics import KinematicsEngine
from surakshaedge.edge.audio import AudioScorer, SAMPLE_RATE
from surakshaedge.edge.fusion import FusionGate
from surakshaedge.edge.pose import KP, Track


def make_track(tid, cx, cy, scale=1.0):
    kp = np.zeros((17, 3))
    kp[:, 2] = 1.0
    kp[KP["left_shoulder"]] = [cx-30*scale, cy-60*scale, 1.0]
    kp[KP["right_shoulder"]] = [cx+30*scale, cy-60*scale, 1.0]
    kp[KP["left_hip"]] = [cx-20*scale, cy+20*scale, 1.0]
    kp[KP["right_hip"]] = [cx+20*scale, cy+20*scale, 1.0]
    kp[KP["left_wrist"]] = [cx-35*scale, cy+20*scale, 1.0]
    kp[KP["right_wrist"]] = [cx+35*scale, cy+20*scale, 1.0]
    kp[KP["left_elbow"]] = [cx-40*scale, cy-20*scale, 1.0]
    kp[KP["right_elbow"]] = [cx+40*scale, cy-20*scale, 1.0]
    kp[KP["left_knee"]] = [cx-20*scale, cy+70*scale, 1.0]
    kp[KP["right_knee"]] = [cx+20*scale, cy+70*scale, 1.0]
    bbox = np.array([cx-50*scale, cy-80*scale, cx+50*scale, cy+140*scale])
    return Track(track_id=tid, keypoints=kp, bbox=bbox, ts_ns=0)


class TestIT03_VisionOnly:
    """IT-03: Vision-only clip should produce ADVISORY, never ALERT."""

    def test_high_kinematic_no_audio_gives_advisory(self):
        kin = KinematicsEngine(k_threshold=0.01, k_persist_s=0.2)
        gate = FusionGate(gate_s=1.5, cooldown_s=10.0)
        S_t = 0.0
        S_flag = False
        decisions = []
        t = 10_000_000_000

        for i in range(20):
            # Move wrist aggressively
            track = make_track(1, 100 + i*5, 200)
            kscore = kin.update([track], t)
            d = gate.update(kin.flag, S_flag, kscore.K_t, S_t, t)
            decisions.append(d.tier)
            t += 100_000_000  # 100ms per frame

        assert "ALERT" not in decisions, "Vision-only scenario must not produce ALERT"


class TestIT04_AudioOnly:
    """IT-04: Audio-only clip should produce ADVISORY, never ALERT."""

    def test_high_audio_no_vision_gives_advisory(self):
        gate = FusionGate(gate_s=1.5, cooldown_s=10.0)
        decisions = []
        t = 10_000_000_000

        # Inject high S_t with no K flag
        for i in range(10):
            d = gate.update(False, True, 0.1, 0.92, t)
            decisions.append(d.tier)
            t += 100_000_000

        assert "ALERT" not in decisions, "Audio-only scenario must not produce ALERT"


class TestIT09_MissingAudio:
    """IT-09: Missing audio channel → vision-only advisory mode."""

    def test_no_audio_source_does_not_crash(self):
        scorer = AudioScorer(model_path=None, s_threshold=0.70)
        # Don't feed any chunks — flag should stay False
        assert scorer.flag is False

    def test_audio_scorer_flag_false_with_no_input(self):
        scorer = AudioScorer(model_path=None)
        assert not scorer.flag
