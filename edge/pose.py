"""
SurakshaEdge - Pose and tracking module
YOLOv8-Pose → Track dataclass with 17 COCO keypoints and a bounding box.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List

import numpy as np

logger = logging.getLogger(__name__)

# COCO-17 keypoint indices
KP = {
    "nose": 0,
    "left_eye": 1, "right_eye": 2,
    "left_ear": 3, "right_ear": 4,
    "left_shoulder": 5, "right_shoulder": 6,
    "left_elbow": 7, "right_elbow": 8,
    "left_wrist": 9, "right_wrist": 10,
    "left_hip": 11, "right_hip": 12,
    "left_knee": 13, "right_knee": 14,
    "left_ankle": 15, "right_ankle": 16,
}

CONF_THRESH = 0.5   # minimum keypoint confidence
MIN_TORSO_PX = 20   # minimum torso length in pixels


@dataclass
class Track:
    track_id: int
    keypoints: np.ndarray   # shape (17, 3): x, y, conf
    bbox: np.ndarray        # shape (4,): x1, y1, x2, y2
    ts_ns: int = 0


class PoseEstimator:
    """Wraps Ultralytics YOLOv8-Pose model with ByteTrack."""

    def __init__(self, model_path: str = "yolov8n-pose.pt", imgsz: int = 640, device: str = "cpu"):
        self.device = device
        self.imgsz = imgsz
        self._model = None
        self._model_path = model_path
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            self._model = YOLO(self._model_path)
            # Warm up with dummy inference to prevent cold-start latency spike on first frame
            dummy = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
            self._model.predict(dummy, imgsz=self.imgsz, device=self.device, verbose=False)
            logger.info("YOLOv8-Pose loaded and warmed up: %s on %s", self._model_path, self.device)
        except Exception as e:
            logger.error("Failed to load pose model: %s", e)
            self._model = None

    def predict(self, img: np.ndarray, ts_ns: int) -> List[Track]:
        """Run pose estimation + tracking. Returns list of Track objects."""
        if self._model is None:
            return []

        t0 = time.perf_counter_ns()
        try:
            results = self._model.track(
                img,
                persist=True,
                imgsz=self.imgsz,
                conf=0.4,
                device=self.device,
                verbose=False,
                tracker="bytetrack.yaml",
            )
        except Exception as e:
            logger.error("Pose inference error: %s", e)
            return []

        tracks = []
        if results and len(results) > 0:
            r = results[0]
            if r.keypoints is not None and r.boxes is not None:
                kps = r.keypoints.data.cpu().numpy()   # (N, 17, 3)
                boxes = r.boxes.xyxy.cpu().numpy()     # (N, 4)
                ids_raw = r.boxes.id
                if ids_raw is not None:
                    ids = ids_raw.cpu().numpy().astype(int)
                else:
                    ids = np.arange(len(boxes))

                for i, (kp, box, tid) in enumerate(zip(kps, boxes, ids)):
                    tracks.append(Track(
                        track_id=int(tid),
                        keypoints=kp,
                        bbox=box,
                        ts_ns=ts_ns,
                    ))

        # Limit to 10 largest tracks by bbox area
        if len(tracks) > 10:
            areas = [(t.bbox[2]-t.bbox[0])*(t.bbox[3]-t.bbox[1]) for t in tracks]
            order = np.argsort(areas)[::-1][:10]
            tracks = [tracks[i] for i in order]

        elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
        logger.debug("Pose: %d tracks in %.1f ms", len(tracks), elapsed_ms)
        return tracks
