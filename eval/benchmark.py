"""
SurakshaEdge - Performance benchmark
Run 1000 frames through each pipeline stage and report p50/p95/p99.

Usage:
    python eval/benchmark.py --frames 1000 --device cpu
    python eval/benchmark.py --frames 1000 --device cuda
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def run_benchmark(n_frames: int = 1000, device: str = "cpu", warmup: int = 100, imgsz: int = 640):
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from surakshaedge.edge.pose import PoseEstimator
    from surakshaedge.edge.kinematics import KinematicsEngine
    from surakshaedge.edge.audio import AudioScorer, SAMPLE_RATE
    from surakshaedge.edge.fusion import FusionGate

    model_path = "models/yolov8s-pose.pt" if device == "cuda" else "models/yolov8n-pose.pt"
    pose       = PoseEstimator(model_path=model_path, imgsz=imgsz, device=device)
    kinematics = KinematicsEngine()
    audio      = AudioScorer()
    gate       = FusionGate()

    model_loaded = pose._model is not None

    frame   = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    achunk  = np.random.randn(int(0.25 * SAMPLE_RATE)).astype(np.float32) * 0.01

    times: dict = {s: [] for s in ("pose", "kinematics", "audio", "fusion", "total")}

    if model_loaded:
        logger.info("Warm-up: %d frames …", warmup)
        for _ in range(warmup):
            pose.predict(frame, time.monotonic_ns())
    else:
        logger.warning(
            "YOLOv8 model not found at %s. "
            "Pose stage will return empty tracks (0 ms). "
            "Download the model first: python -c \"from ultralytics import YOLO; YOLO('yolov8n-pose.pt')\"",
            model_path,
        )
        logger.warning("Benchmark results EXCLUDE pose latency — model must be present for valid numbers.")

    logger.info("Benchmarking %d frames on device=%s imgsz=%d …", n_frames, device, imgsz)
    S_t = 0.0; S_flag = False

    for _ in range(n_frames):
        ts   = time.monotonic_ns()
        t_all = time.perf_counter_ns()

        t0 = time.perf_counter_ns()
        tracks = pose.predict(frame, ts)
        times["pose"].append((time.perf_counter_ns() - t0) / 1e6)

        t0 = time.perf_counter_ns()
        kscore = kinematics.update(tracks, ts)
        times["kinematics"].append((time.perf_counter_ns() - t0) / 1e6)

        t0 = time.perf_counter_ns()
        r = audio.update(achunk, ts)
        if r:
            S_t = r.S_t; S_flag = audio.flag
        times["audio"].append((time.perf_counter_ns() - t0) / 1e6)

        t0 = time.perf_counter_ns()
        gate.update(kinematics.flag, S_flag, kscore.K_t, S_t, ts)
        times["fusion"].append((time.perf_counter_ns() - t0) / 1e6)

        times["total"].append((time.perf_counter_ns() - t_all) / 1e6)

    print(f"\n{'Stage':<18} {'p50':>8} {'p95':>8} {'p99':>8} {'mean':>8}")
    print("-" * 50)
    for stage, vals in times.items():
        a = np.array(vals)
        print(f"{stage:<18} {np.percentile(a,50):>7.1f}ms {np.percentile(a,95):>7.1f}ms "
              f"{np.percentile(a,99):>7.1f}ms {a.mean():>7.1f}ms")

    fps = n_frames / (sum(times["total"]) / 1000)
    p95 = np.percentile(np.array(times["total"]), 95)
    target_fps = 25 if device == "cuda" else 8
    print(f"\nThroughput : {fps:.1f} FPS  (target ≥{target_fps})")
    print(f"p95 total  : {p95:.1f} ms   (target ≤35 ms on GPU)")
    print(f"FPS target : {'✅' if fps >= target_fps else '❌'}")

    return times


def main():
    p = argparse.ArgumentParser(description="SurakshaEdge performance benchmark")
    p.add_argument("--frames",  type=int, default=1000)
    p.add_argument("--device",  default="cpu")
    p.add_argument("--warmup",  type=int, default=100)
    p.add_argument("--imgsz",   type=int, default=640)
    args = p.parse_args()
    run_benchmark(n_frames=args.frames, device=args.device, warmup=args.warmup, imgsz=args.imgsz)


if __name__ == "__main__":
    main()
