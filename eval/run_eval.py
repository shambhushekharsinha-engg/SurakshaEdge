"""
SurakshaEdge - Evaluation harness
Replays labelled clips and measures recall, FAR, latency.
Usage: python eval/run_eval.py --split validation --config configs/demo.yaml
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def wilson_interval(k: int, n: int, z: float = 1.96):
    """95% Wilson confidence interval for proportion k/n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2*n)) / denom
    margin = z * (p*(1-p)/n + z**2/(4*n**2))**0.5 / denom
    return (max(0.0, centre - margin), min(1.0, centre + margin))


class EvalRunner:
    def __init__(self, config_path: str, split: str = "test", clips_dir: str = "data/clips"):
        self.split = split
        self.clips_dir = Path(clips_dir)
        self.config_path = config_path
        self.results: List[Dict[str, Any]] = []

    def load_labels(self, labels_path: str = "eval/labels.csv") -> List[Dict]:
        clips = []
        if not Path(labels_path).exists():
            logger.warning("labels.csv not found at %s", labels_path)
            return clips
        with open(labels_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("split", "") == self.split or self.split == "all":
                    clips.append(row)
        return clips

    def run(self):
        clips = self.load_labels()
        if not clips:
            logger.warning("No clips found for split '%s'. Showing simulation results.", self.split)
            self._show_simulation_summary()
            return

        positives = [c for c in clips if c["class"] == "positive"]
        negatives = [c for c in clips if c["class"] == "hard_negative"]

        tp = 0; fp = 0; fn = 0; tn = 0
        latencies = []

        for clip in clips:
            clip_path = self.clips_dir / f"{clip['clip_id']}.mp4"
            expected = clip["expected_tier"]

            if not clip_path.exists():
                logger.warning("Clip not found: %s (skipping)", clip_path)
                continue

            result = self._eval_clip(clip, clip_path)
            self.results.append(result)

            got_alert = result.get("detected_tier") in ("ALERT",)
            got_advisory = result.get("detected_tier") in ("ADVISORY",)

            if expected == "ALERT":
                if got_alert:
                    tp += 1
                    if result.get("latency_s") is not None:
                        latencies.append(result["latency_s"])
                else:
                    fn += 1
            elif expected == "NONE":
                if got_alert:
                    fp += 1
                else:
                    tn += 1

        # Compute metrics
        total_pos = tp + fn
        total_neg = fp + tn

        recall = tp / total_pos if total_pos > 0 else 0.0
        far = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        recall_ci = wilson_interval(tp, total_pos)
        far_ci = wilson_interval(fp, fp + tn)

        lat_arr = np.array(latencies) if latencies else np.array([0.0])

        print("\n" + "="*60)
        print("SURAKSHAEDGE EVALUATION RESULTS")
        print("="*60)
        print(f"Split: {self.split}")
        print(f"Clips evaluated: {len(self.results)} / {len(clips)}")
        print(f"\nRecall (event-level): {recall:.1%} [{recall_ci[0]:.1%}, {recall_ci[1]:.1%}] (target >=85%)")
        print(f"False Alarm Rate:     {far:.1%} [{far_ci[0]:.1%}, {far_ci[1]:.1%}] (target <5%)")
        print(f"TP: {tp}  FP: {fp}  FN: {fn}  TN: {tn}")
        if len(lat_arr) > 0 and lat_arr.max() > 0:
            print(f"Latency to alert: median={np.median(lat_arr):.2f}s p95={np.percentile(lat_arr, 95):.2f}s")
        print("="*60)

        target_recall = recall >= 0.85
        target_far = far < 0.05
        print(f"Recall target {'PASS' if target_recall else 'FAIL'}")
        print(f"FAR target    {'PASS' if target_far else 'FAIL'}")

    def _eval_clip(self, clip: Dict, clip_path: Path) -> Dict[str, Any]:
        """
        Replay a clip through the pipeline and capture the first alert.
        Returns a result dict.
        """
        # Import pipeline modules
        try:

            import yaml
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from surakshaedge.edge.audio import AudioScorer
            from surakshaedge.edge.fusion import FusionGate
            from surakshaedge.edge.kinematics import KinematicsEngine
            from surakshaedge.edge.pose import PoseEstimator

            with open(self.config_path) as f:
                config = yaml.safe_load(f)

            vision_cfg = config.get("vision", {})
            audio_cfg = config.get("audio", {})
            fusion_cfg = config.get("fusion", {})

            device = "cpu"
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
            except ImportError:
                pass

            pose = PoseEstimator(
                model_path=vision_cfg.get("model", "yolov8n-pose.pt"),
                imgsz=vision_cfg.get("imgsz", 640),
                device=device,
            )
            kinematics = KinematicsEngine(
                weights=vision_cfg.get("weights"),
                k_threshold=vision_cfg.get("k_threshold", 0.62),
                k_persist_s=vision_cfg.get("k_persist_s", 0.4),
            )
            audio_scorer = AudioScorer(
                model_path=audio_cfg.get("model"),
                s_threshold=audio_cfg.get("s_threshold", 0.70),
            )
            gate = FusionGate(
                gate_s=fusion_cfg.get("gate_s", 1.5),
                cooldown_s=fusion_cfg.get("cooldown_s", 10.0),
            )

            import cv2
            cap = cv2.VideoCapture(str(clip_path))
            onset_s = float(clip.get("onset_s", 0.0))
            first_alert_s = None
            frame_count = 0
            S_t = 0.0
            S_flag = False

            while cap.isOpened():
                ret, img = cap.read()
                if not ret:
                    break
                ts_ns = int(time.monotonic_ns())
                tracks = pose.predict(img, ts_ns)
                kscore = kinematics.update(tracks, ts_ns)
                decision = gate.update(
                    k_flag=kinematics.flag,
                    s_flag=S_flag,
                    K_t=kscore.K_t,
                    S_t=S_t,
                    ts_ns=ts_ns,
                )
                if decision.tier != "NONE" and first_alert_s is None:
                    elapsed_s = frame_count / cap.get(cv2.CAP_PROP_FPS) if cap.get(cv2.CAP_PROP_FPS) > 0 else 0
                    latency_s = max(0.0, elapsed_s - onset_s)
                    first_alert_s = elapsed_s
                    cap.release()
                    return {
                        "clip_id": clip["clip_id"],
                        "expected_tier": clip["expected_tier"],
                        "detected_tier": decision.tier,
                        "latency_s": latency_s,
                        "K_t": kscore.K_t,
                        "S_t": S_t,
                    }
                frame_count += 1

            cap.release()
            return {
                "clip_id": clip["clip_id"],
                "expected_tier": clip["expected_tier"],
                "detected_tier": "NONE",
                "latency_s": None,
            }
        except Exception as e:
            logger.error("Error evaluating %s: %s", clip["clip_id"], e)
            return {
                "clip_id": clip["clip_id"],
                "expected_tier": clip["expected_tier"],
                "detected_tier": "ERROR",
                "error": str(e),
            }

    def _show_simulation_summary(self):
        print("\nNo clips found. Run with recorded clips in data/clips/")
        print("Expected clip naming: CLASS_SESSION_SCENE_TAKE.mp4")
        print("Example: POS_S01_gate_T01.mp4")


def main():
    parser = argparse.ArgumentParser(description="SurakshaEdge evaluation harness")
    parser.add_argument("--split", default="test", choices=["dev", "validation", "test", "all"])
    parser.add_argument("--config", default="configs/demo.yaml")
    parser.add_argument("--clips-dir", default="data/clips")
    args = parser.parse_args()

    runner = EvalRunner(config_path=args.config, split=args.split, clips_dir=args.clips_dir)
    runner.run()


if __name__ == "__main__":
    main()
