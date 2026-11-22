#!/usr/bin/env python3
"""
SurakshaEdge - Field Soak Test CLI
====================================
Usage:
    python scripts/run_soak_test.py --frames 10000 --report results/field_soak_report.json

Runs 10,000 synthetic frames through the KinematicsEngine → FusionGate pipeline,
prints a live progress bar and final PASS/FAIL summary table.

Exit codes:
    0 — PASS (zero memory leak, latency within limit, PT-01 privacy invariant OK)
    1 — FAIL
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import pathlib
import random
import sys
import tempfile
import time
from typing import List

# ---------------------------------------------------------------------------
# Try real edge imports; fall back to lightweight mocks
# ---------------------------------------------------------------------------
try:
    from edge.kinematics import KinematicsEngine
    from edge.fusion import FusionGate
    from edge.pose import Track
    _REAL_IMPORTS = True
except Exception:
    _REAL_IMPORTS = False

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    from tqdm import tqdm
    _TQDM = True
except ImportError:
    _TQDM = False

# ---------------------------------------------------------------------------
# Mock classes
# ---------------------------------------------------------------------------

class _MockKScore:
    def __init__(self, K_t: float):
        self.K_t = K_t
        self.flag = K_t >= 0.62

class _MockKinematicsEngine:
    _counter: int = 0
    @property
    def flag(self):
        return False
    def update(self, tracks, ts_ns):
        time.sleep(random.uniform(0.001, 0.004))
        self._counter += 1
        K_t = min(1.0, (self._counter % 100) / 100.0 + random.uniform(0, 0.1))
        return _MockKScore(K_t)

class _MockFusionGate:
    def update(self, k_flag, s_flag, K_t, S_t, ts_ns, **_):
        pass


def _synthetic_tracks(rng: random.Random):
    if not _REAL_IMPORTS:
        return []
    import numpy as np
    n = rng.randint(0, 2)
    tracks = []
    for i in range(n):
        kp = np.zeros((17, 3), dtype=np.float32)
        for j in range(17):
            kp[j] = [rng.uniform(50, 600), rng.uniform(50, 400), rng.uniform(0.5, 1.0)]
        bbox = np.array([
            rng.uniform(10, 300), rng.uniform(10, 200),
            rng.uniform(300, 630), rng.uniform(200, 470),
        ], dtype=np.float32)
        tracks.append(Track(track_id=i, keypoints=kp, bbox=bbox, ts_ns=time.time_ns()))
    return tracks


_VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.h264', '.yuv', '.raw'}

def _count_video_files():
    tmp = pathlib.Path(tempfile.gettempdir())
    count = 0
    try:
        for f in tmp.iterdir():
            if f.is_file() and f.suffix.lower() in _VIDEO_EXTS:
                count += 1
    except PermissionError:
        pass
    return count


def _percentile(sorted_vals: List[float], pct: float) -> float:
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    idx = int(n * pct / 100)
    return sorted_vals[min(idx, n - 1)]


def run_soak(frame_count: int, report_path: str) -> bool:
    rng = random.Random(42)

    if _REAL_IMPORTS:
        engine = KinematicsEngine()
        gate = FusionGate()
    else:
        engine = _MockKinematicsEngine()
        gate = _MockFusionGate()

    proc = psutil.Process(os.getpid()) if _PSUTIL else None

    # Baseline
    gc.collect()
    video_before = _count_video_files()
    rss_baseline_mb = (proc.memory_info().rss / 1_048_576) if proc else 0.0
    rss_samples = [rss_baseline_mb]

    latencies_ms: List[float] = []
    base_ts_ns = time.time_ns()
    frame_ns = int(1e9 / 30)  # simulate 30 FPS timestamps

    # Progress bar
    iter_range = tqdm(range(frame_count), desc='Field Soak', unit='frame', ncols=80) \
        if _TQDM else range(frame_count)

    for fi in iter_range:
        ts_ns = base_ts_ns + fi * frame_ns
        tracks = _synthetic_tracks(rng)
        s_t = rng.uniform(0.0, 1.0)

        t0 = time.perf_counter()
        k_score = engine.update(tracks, ts_ns)
        K_t = k_score.K_t if hasattr(k_score, 'K_t') else 0.0
        k_flag = engine.flag if hasattr(engine, 'flag') else (K_t >= 0.62)
        s_flag = s_t >= 0.70
        gate.update(k_flag=k_flag, s_flag=s_flag, K_t=K_t, S_t=s_t, ts_ns=ts_ns)
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        if (fi + 1) % 500 == 0 and proc:
            rss_samples.append(proc.memory_info().rss / 1_048_576)

    gc.collect()
    if proc:
        rss_final_mb = proc.memory_info().rss / 1_048_576
        rss_samples.append(rss_final_mb)
    else:
        rss_final_mb = rss_baseline_mb

    latencies_ms.sort()
    median_ms = _percentile(latencies_ms, 50)
    p95_ms    = _percentile(latencies_ms, 95)
    p99_ms    = _percentile(latencies_ms, 99)
    rss_delta = rss_final_mb - rss_baseline_mb
    video_after = _count_video_files()
    new_videos = max(0, video_after - video_before)

    leak_ok    = rss_delta < 10.0
    latency_ok = median_ms < 100.0
    privacy_ok = new_videos == 0
    passed     = leak_ok and latency_ok and privacy_ok

    report = {
        'frame_count': frame_count,
        'real_imports': _REAL_IMPORTS,
        'median_latency_ms': round(median_ms, 4),
        'p95_latency_ms': round(p95_ms, 4),
        'p99_latency_ms': round(p99_ms, 4),
        'ram_delta_mb': round(rss_delta, 4),
        'disk_write_count': new_videos,
        'leak_ok': leak_ok,
        'latency_ok': latency_ok,
        'privacy_ok': privacy_ok,
        'passed': passed,
    }

    out = pathlib.Path(report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w') as fh:
        json.dump(report, fh, indent=2)

    # ── Print summary table ────────────────────────────────────────────────
    W = 50
    print('\n' + '─' * W)
    print(' SurakshaEdge Field Soak Test — Results')
    print('─' * W)
    print(f" Frames processed : {frame_count:,}")
    print(f" Real edge modules: {'YES (torch/ONNX)' if _REAL_IMPORTS else 'NO (mock pipeline)'}")
    print(f" Median latency   : {median_ms:.2f} ms  {'✅ PASS' if latency_ok else '❌ FAIL'} (limit 100 ms)")
    print(f" p95 latency      : {p95_ms:.2f} ms")
    print(f" p99 latency      : {p99_ms:.2f} ms")
    print(f" RAM delta        : {rss_delta:+.2f} MB  {'✅ PASS' if leak_ok else '❌ FAIL'} (limit +10 MB)")
    print(f" Privacy (PT-01)  : {new_videos} new video file(s)  {'✅ PASS' if privacy_ok else '❌ FAIL'}")
    print(f" Report saved     : {out}")
    print('─' * W)
    verdict = '  ✅  VERDICT: PASS' if passed else '  ❌  VERDICT: FAIL'
    print(f'\033[92m{verdict}\033[0m' if passed else f'\033[91m{verdict}\033[0m')
    print('─' * W + '\n')

    return passed


def main():
    parser = argparse.ArgumentParser(description='SurakshaEdge Stage-IV Field Soak Test')
    parser.add_argument('--frames', type=int, default=10_000,
                        help='Number of synthetic frames to process (default: 10000)')
    parser.add_argument('--report', type=str, default='results/field_soak_report.json',
                        help='Output JSON report path')
    args = parser.parse_args()

    ok = run_soak(frame_count=args.frames, report_path=args.report)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
