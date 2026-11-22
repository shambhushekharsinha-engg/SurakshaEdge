"""
SurakshaEdge - Main edge pipeline
Orchestrates: ingest → pose → kinematics → audio → fusion → dispatch

Run as:
    python -m surakshaedge.edge.pipeline --config configs/demo.yaml
    python -m surakshaedge.edge.pipeline --config configs/demo.yaml --source data/clips/POS_S01_gate_T01.mp4
"""
from __future__ import annotations

import argparse
import logging
import os
import os as _os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

_os.environ.setdefault("MPLCONFIGDIR", _os.path.join(_os.path.expanduser("~"), ".config", "matplotlib"))

from .audio import AudioScorer
from .fusion import FusionGate
from .ingest import AudioChunk, AudioIngest, Frame, VideoIngest
from .kinematics import KinematicsEngine
from .pose import PoseEstimator
from .privacy import PrivacyManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("pipeline")


class StageTiming:
    """Collects per-stage latency samples and reports percentiles."""

    def __init__(self):
        self._times: Dict[str, list] = {}

    def record(self, stage: str, ms: float):
        self._times.setdefault(stage, []).append(ms)

    def summary(self) -> Dict[str, Dict[str, float]]:
        import numpy as np
        out = {}
        for stage, vals in self._times.items():
            if vals:
                a = np.array(vals)
                out[stage] = {
                    "p50": float(np.percentile(a, 50)),
                    "p95": float(np.percentile(a, 95)),
                    "p99": float(np.percentile(a, 99)),
                    "count": len(vals),
                }
        return out


class Pipeline:
    def __init__(self, config: Dict[str, Any], source_override: Optional[str] = None):
        self.config = config
        self.timing = StageTiming()
        self._stop = threading.Event()

        self._frame_q: queue.Queue = queue.Queue(maxsize=2)
        self._audio_q: queue.Queue = queue.Queue(maxsize=8)

        cam_cfg = config["cameras"][0]
        self.camera_id: str = cam_cfg["id"]
        self.gps: Dict[str, float] = {"lat": cam_cfg["gps"][0], "lon": cam_cfg["gps"][1]}

        source = source_override or cam_cfg["source"]
        audio_source = cam_cfg.get("audio_source", None)

        self._video_ingest = VideoIngest(
            source=source,
            out_q=self._frame_q,
            replay_mode=isinstance(source, str) and Path(str(source)).is_file(),
        )
        self._audio_ingest = AudioIngest(
            source=audio_source,
            out_q=self._audio_q,
            device=cam_cfg.get("mic_device", None),
        )

        vision_cfg = config.get("vision", {})
        device = "cuda" if self._cuda_available() else "cpu"
        self._pose = PoseEstimator(
            model_path=vision_cfg.get("model", "yolov8n-pose.pt"),
            imgsz=vision_cfg.get("imgsz", 640),
            device=device,
        )
        self._kinematics = KinematicsEngine(
            weights=vision_cfg.get("weights"),
            k_threshold=vision_cfg.get("k_threshold", 0.62),
            k_persist_s=vision_cfg.get("k_persist_s", 0.4),
        )

        audio_cfg = config.get("audio", {})
        self._audio_scorer = AudioScorer(
            model_path=audio_cfg.get("model"),
            s_threshold=audio_cfg.get("s_threshold", 0.70),
        )
        # Expose audio mode via env var so the API /health endpoint can report it
        os.environ["SURAKSHA_AUDIO_MODE"] = self._audio_scorer.mode
        if self._audio_scorer.mode == "energy_fallback":
            logger.warning(
                "Audio mode: ENERGY FALLBACK. "
                "S_t detects ANY loud sound, not specifically screams. "
                "Train models/audio_cnn.onnx and set audio.model in config to enable MFCC-CNN."
            )

        fusion_cfg = config.get("fusion", {})
        self._fusion = FusionGate(
            gate_s=fusion_cfg.get("gate_s", 1.5),
            cooldown_s=fusion_cfg.get("cooldown_s", 10.0),
        )

        priv_cfg = config.get("privacy", {})
        os.makedirs("results", exist_ok=True)
        self._privacy = PrivacyManager(
            buffer_s=priv_cfg.get("buffer_s", 5.0),
            retention_hours=priv_cfg.get("retention_hours", 24.0),
            audit_log_path="results/audit.jsonl",
        )

        api_cfg = config.get("api", {})
        self._api_url = f"http://{api_cfg.get('host', '127.0.0.1')}:{api_cfg.get('port', 8000)}"
        self._api_token = os.environ.get("SURAKSHA_API_TOKEN", "demo-token")

        self._latest_S_t: float = 0.0
        self._latest_S_flag: bool = False
        self._frame_count: int = 0

    @staticmethod
    def _cuda_available() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def run(self):
        logger.info("Pipeline starting — camera: %s  device: %s",
                    self.camera_id, "cuda" if self._cuda_available() else "cpu")
        self._video_ingest.start()
        self._audio_ingest.start()

        audio_t = threading.Thread(target=self._audio_loop, daemon=True, name="AudioLoop")
        audio_t.start()

        try:
            self._vision_loop()
        except KeyboardInterrupt:
            logger.info("Interrupted.")
        finally:
            self._stop.set()
            self._video_ingest.stop()
            self._audio_ingest.stop()
            import json
            logger.info("Stage timing:\n%s", json.dumps(self.timing.summary(), indent=2))

    # ------------------------------------------------------------------
    def _audio_loop(self):
        while not self._stop.is_set():
            try:
                chunk: AudioChunk = self._audio_q.get(timeout=0.5)
            except queue.Empty:
                continue
            t0 = time.perf_counter_ns()
            score = self._audio_scorer.update(chunk.pcm16k, chunk.ts_ns)
            if score is not None:
                self._latest_S_t = score.S_t
                self._latest_S_flag = self._audio_scorer.flag
            self.timing.record("audio", (time.perf_counter_ns() - t0) / 1e6)

    def _vision_loop(self):
        while not self._stop.is_set():
            try:
                frame: Frame = self._frame_q.get(timeout=0.5)
            except queue.Empty:
                if not self._video_ingest.is_alive():
                    logger.info("Video ingest ended — stopping pipeline.")
                    break
                continue

            t_start = time.perf_counter_ns()
            self._privacy.push_frame(frame.img, frame.ts_ns)

            t0 = time.perf_counter_ns()
            tracks = self._pose.predict(frame.img, frame.ts_ns)
            self.timing.record("pose", (time.perf_counter_ns() - t0) / 1e6)

            t0 = time.perf_counter_ns()
            kscore = self._kinematics.update(tracks, frame.ts_ns)
            self.timing.record("kinematics", (time.perf_counter_ns() - t0) / 1e6)

            t0 = time.perf_counter_ns()
            decision = self._fusion.update(
                k_flag=self._kinematics.flag,
                s_flag=self._latest_S_flag,
                K_t=kscore.K_t,
                S_t=self._latest_S_t,
                ts_ns=frame.ts_ns,
                track_ids=kscore.track_ids,
            )
            self.timing.record("fusion", (time.perf_counter_ns() - t0) / 1e6)

            pipeline_ms = (time.perf_counter_ns() - t_start) / 1e6
            self.timing.record("pipeline_total", pipeline_ms)
            self._frame_count += 1

            if decision.tier != "NONE":
                self._dispatch(decision, tracks, pipeline_ms)

            if self._frame_count % 30 == 0:
                logger.info(
                    "HUD | frame=%d K_t=%.2f S_t=%.2f tier=%-8s pose=%.1fms total=%.1fms",
                    self._frame_count, kscore.K_t, self._latest_S_t,
                    decision.tier, self.timing._times.get("pose", [0])[-1], pipeline_ms,
                )

    def _dispatch(self, decision, tracks, pipeline_ms: float):
        t0 = time.perf_counter_ns()
        bboxes = [t.bbox.tolist() for t in tracks]
        packet = self._privacy.build_event_packet(
            camera_id=self.camera_id,
            tier=decision.tier,
            gps=self.gps,
            K_t=decision.K_t,
            S_t=decision.S_t,
            dt_s=max(decision.dt_s, 0.0),
            bboxes=bboxes,
            pipeline_ms=pipeline_ms,
            dispatch_ms=0.0,
        )
        dispatch_ms = (time.perf_counter_ns() - t0) / 1e6
        packet.latency_ms["dispatch"] = round(dispatch_ms, 2)

        payload = {
            "event_id":   packet.event_id,
            "camera_id":  packet.camera_id,
            "ts_utc":     packet.ts_utc,
            "tier":       packet.tier,
            "gps":        packet.gps,
            "scores":     packet.scores,
            "bboxes":     packet.bboxes,
            "clip_enc":   packet.clip_enc,
            "latency_ms": packet.latency_ms,
        }

        try:
            import requests
            resp = requests.post(
                f"{self._api_url}/events",
                json=payload,
                headers={"Authorization": f"Bearer {self._api_token}"},
                timeout=2.0,
            )
            logger.info("Dispatched %s event %s → HTTP %d", decision.tier, packet.event_id[:8], resp.status_code)
        except Exception as e:
            logger.warning("Dispatch failed (API may not be running): %s", e)

        self.timing.record("dispatch", dispatch_ms)


# ------------------------------------------------------------------

def load_config(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="SurakshaEdge edge pipeline")
    parser.add_argument("--config", default="configs/demo.yaml")
    parser.add_argument("--source", default=None, help="Override video source (file path, webcam index, RTSP URL)")
    args = parser.parse_args()

    config = load_config(args.config)
    pipeline = Pipeline(config, source_override=args.source)
    pipeline.run()


if __name__ == "__main__":
    main()
