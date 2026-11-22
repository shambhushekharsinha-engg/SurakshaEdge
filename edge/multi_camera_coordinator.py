"""
SurakshaEdge - Multi-Camera Campus Coordinator
===============================================
Manages up to 5 concurrent camera streams, each running in its own thread.
Features:
  - Per-camera heartbeat watchdog (3s timeout → CAMERA_TAMPER alert)
  - Thread-safe consolidated alert queue for dashboard dispatch
  - Graceful shutdown with 5s join timeout

Usage:
    coordinator = MultiCameraCoordinator(max_cameras=5)
    coordinator.start([
        {"camera_id": "gate1", "is_synthetic": True, "gps": (28.459, 77.493)},
        {"camera_id": "hostel_road", "is_synthetic": True, "gps": (28.460, 77.491)},
    ])
    alert = coordinator.get_next_alert(timeout=1.0)
    coordinator.stop()
"""
from __future__ import annotations

import logging
import queue
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Heartbeat watchdog: if no frame received within this window → CAMERA_TAMPER
HEARTBEAT_TIMEOUT_S: float = 3.0
# Maximum cameras supported
MAX_CAMERAS: int = 5
# Synthetic pipeline: simulated frame interval
SYNTHETIC_FRAME_INTERVAL_S: float = 1.0 / 18.0  # ~18 FPS synthetic


@dataclass
class CameraConfig:
    camera_id: str
    is_synthetic: bool = True
    feed_url: Optional[str] = None          # real RTSP/RTMP URL for live feeds
    gps: tuple = (28.4595, 77.4931)         # (lat, lon) — default GNIOT Gate-1
    zone: str = "unknown"


@dataclass
class AlertEvent:
    camera_id: str
    event_type: str                          # "ALERT" | "ADVISORY" | "CAMERA_TAMPER"
    K_t: float = 0.0
    S_t: float = 0.0
    gps: tuple = (0.0, 0.0)
    timestamp_s: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


class _CameraWorker:
    """
    Single-camera pipeline thread.
    Runs a simplified synthetic pipeline loop (or hooks into real PoseEstimator if available).
    Posts AlertEvents to the shared consolidated queue.
    Updates self.last_frame_ts on every processed frame so the watchdog can monitor it.
    """

    def __init__(
        self,
        config: CameraConfig,
        alert_queue: "queue.Queue[AlertEvent]",
        stop_event: threading.Event,
    ):
        self.config = config
        self._queue = alert_queue
        self._stop = stop_event
        self.last_frame_ts: float = time.time()
        self._thread: Optional[threading.Thread] = None

        # Try importing real edge modules; fall back to mock pipeline
        try:
            from edge.fusion import FusionGate
            from edge.kinematics import KinematicsEngine
            self._kinematics = KinematicsEngine()
            self._gate = FusionGate()
            self._real_pipeline = True
        except Exception:
            self._kinematics = None
            self._gate = None
            self._real_pipeline = False

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run,
            name=f"cam-{self.config.camera_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info("[%s] Camera worker started (real_pipeline=%s)",
                    self.config.camera_id, self._real_pipeline)

    def join(self, timeout: float = 5.0) -> None:
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self) -> None:
        rng = random.Random()
        frame_idx = 0

        while not self._stop.is_set():
            t_frame_start = time.time()
            ts_ns = time.time_ns()

            try:
                K_t, S_t, tier = self._process_frame(frame_idx, ts_ns, rng)
                self.last_frame_ts = time.time()

                if tier in ("ALERT", "ADVISORY"):
                    event = AlertEvent(
                        camera_id=self.config.camera_id,
                        event_type=tier,
                        K_t=round(K_t, 4),
                        S_t=round(S_t, 4),
                        gps=self.config.gps,
                        details={"frame_idx": frame_idx, "real_pipeline": self._real_pipeline},
                    )
                    try:
                        self._queue.put_nowait(event)
                    except queue.Full:
                        logger.warning("[%s] Alert queue full — dropping event", self.config.camera_id)

            except Exception as exc:
                logger.error("[%s] Frame processing error: %s", self.config.camera_id, exc)

            frame_idx += 1

            # Throttle to ~18 FPS synthetic rate
            elapsed = time.time() - t_frame_start
            sleep_s = max(0.0, SYNTHETIC_FRAME_INTERVAL_S - elapsed)
            self._stop.wait(timeout=sleep_s)  # wake immediately on stop

        logger.info("[%s] Camera worker stopped after %d frames", self.config.camera_id, frame_idx)

    def _process_frame(self, frame_idx: int, ts_ns: int, rng: random.Random):
        """Run one frame through the pipeline. Returns (K_t, S_t, tier)."""
        if self._real_pipeline:
            return self._process_real(frame_idx, ts_ns, rng)
        return self._process_mock(frame_idx, ts_ns, rng)

    def _process_real(self, frame_idx: int, ts_ns: int, rng: random.Random):
        """Real pipeline: synthetic tracks → KinematicsEngine → FusionGate."""
        import numpy as np

        from edge.pose import Track

        # Generate 1-2 synthetic persons
        n_persons = rng.randint(0, 2)
        tracks = []
        for i in range(n_persons):
            kp = np.zeros((17, 3), dtype=np.float32)
            for j in range(17):
                kp[j] = [rng.uniform(50, 600), rng.uniform(50, 400), rng.uniform(0.6, 1.0)]
            bbox = np.array([
                rng.uniform(10, 300), rng.uniform(10, 200),
                rng.uniform(300, 630), rng.uniform(200, 470),
            ], dtype=np.float32)
            tracks.append(Track(track_id=i, keypoints=kp, bbox=bbox, ts_ns=ts_ns))

        k_score = self._kinematics.update(tracks, ts_ns)
        K_t = k_score.K_t
        S_t = rng.uniform(0.0, 1.0)
        s_flag = S_t >= 0.70

        decision = self._gate.update(
            k_flag=self._kinematics.flag,
            s_flag=s_flag,
            K_t=K_t,
            S_t=S_t,
            ts_ns=ts_ns,
        )
        tier = decision.tier if hasattr(decision, "tier") else "NONE"
        return K_t, S_t, tier

    def _process_mock(self, frame_idx: int, ts_ns: int, rng: random.Random):
        """Lightweight mock pipeline for environments without torch/ONNX."""
        # Simulate realistic K_t: mostly low, occasional spike
        cycle = frame_idx % 200
        if 180 <= cycle < 195:
            K_t = rng.uniform(0.65, 0.90)   # simulated assault window
        else:
            K_t = rng.uniform(0.0, 0.40)
        S_t = rng.uniform(0.0, 1.0)
        k_flag = K_t >= 0.62
        s_flag = S_t >= 0.70
        tier = "ALERT" if k_flag and s_flag else "ADVISORY" if k_flag or s_flag else "NONE"
        return K_t, S_t, tier


class MultiCameraCoordinator:
    """
    Manages up to MAX_CAMERAS (5) concurrent camera streams.

    Each camera runs in its own daemon thread with the full pipeline.
    A heartbeat watchdog thread monitors last_frame_ts for each camera
    and raises CAMERA_TAMPER alerts if any feed stalls for >3 seconds.

    Thread-safe alert queue is drained via get_next_alert().
    """

    def __init__(self, max_cameras: int = MAX_CAMERAS):
        self._max_cameras = min(max_cameras, MAX_CAMERAS)
        self._workers: Dict[str, _CameraWorker] = {}
        self._stop_event = threading.Event()
        self._alert_queue: "queue.Queue[AlertEvent]" = queue.Queue(maxsize=500)
        self._watchdog_thread: Optional[threading.Thread] = None
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, camera_configs: List[Dict[str, Any]]) -> None:
        """
        Start camera workers for each config dict.
        Each dict must have 'camera_id'; optionally 'is_synthetic', 'feed_url', 'gps', 'zone'.
        """
        if self._running:
            logger.warning("Coordinator already running — call stop() first")
            return

        if len(camera_configs) > self._max_cameras:
            logger.warning(
                "Requested %d cameras but max is %d — truncating",
                len(camera_configs), self._max_cameras,
            )
            camera_configs = camera_configs[: self._max_cameras]

        self._stop_event.clear()

        for cfg_dict in camera_configs:
            cfg = CameraConfig(
                camera_id=cfg_dict["camera_id"],
                is_synthetic=cfg_dict.get("is_synthetic", True),
                feed_url=cfg_dict.get("feed_url"),
                gps=tuple(cfg_dict.get("gps", (28.4595, 77.4931))),
                zone=cfg_dict.get("zone", cfg_dict["camera_id"]),
            )
            worker = _CameraWorker(cfg, self._alert_queue, self._stop_event)
            self._workers[cfg.camera_id] = worker
            worker.start()

        # Start heartbeat watchdog
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            name="cam-watchdog",
            daemon=True,
        )
        self._watchdog_thread.start()
        self._running = True
        logger.info(
            "[Coordinator] Started %d camera workers + watchdog", len(self._workers)
        )

    def stop(self) -> None:
        """Gracefully stop all workers and watchdog within 5 seconds."""
        if not self._running:
            return
        logger.info("[Coordinator] Stopping %d workers…", len(self._workers))
        self._stop_event.set()

        for camera_id, worker in self._workers.items():
            worker.join(timeout=5.0)
            if worker._thread and worker._thread.is_alive():
                logger.warning("[%s] Worker did not stop within 5s", camera_id)

        if self._watchdog_thread and self._watchdog_thread.is_alive():
            self._watchdog_thread.join(timeout=2.0)

        self._workers.clear()
        self._running = False
        logger.info("[Coordinator] All workers stopped")

    def get_next_alert(self, timeout: float = 1.0) -> Optional[AlertEvent]:
        """
        Return the next AlertEvent from the consolidated queue, or None on timeout.
        Thread-safe; can be called from any thread or async context.
        """
        try:
            return self._alert_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @property
    def camera_ids(self) -> List[str]:
        return list(self._workers.keys())

    @property
    def is_running(self) -> bool:
        return self._running

    def camera_status(self) -> Dict[str, Dict[str, Any]]:
        """Return per-camera status dict: last_frame_age_s, is_alive, camera_id."""
        now = time.time()
        status: Dict[str, Dict[str, Any]] = {}
        for cid, worker in self._workers.items():
            age_s = now - worker.last_frame_ts
            status[cid] = {
                "camera_id": cid,
                "last_frame_age_s": round(age_s, 2),
                "is_alive": worker._thread.is_alive() if worker._thread else False,
                "tamper_suspected": age_s > HEARTBEAT_TIMEOUT_S,
            }
        return status

    # ------------------------------------------------------------------
    # Watchdog
    # ------------------------------------------------------------------

    def _watchdog_loop(self) -> None:
        """Monitor all cameras for heartbeat timeout. Posts CAMERA_TAMPER to alert queue."""
        logger.info("[Watchdog] Heartbeat monitor started (timeout=%.1fs)", HEARTBEAT_TIMEOUT_S)
        tamper_flagged: set = set()

        while not self._stop_event.is_set():
            now = time.time()
            for camera_id, worker in list(self._workers.items()):
                age_s = now - worker.last_frame_ts
                if age_s > HEARTBEAT_TIMEOUT_S and camera_id not in tamper_flagged:
                    logger.warning(
                        "[Watchdog] CAMERA_TAMPER: camera '%s' stalled for %.1fs",
                        camera_id, age_s,
                    )
                    tamper_event = AlertEvent(
                        camera_id=camera_id,
                        event_type="CAMERA_TAMPER",
                        K_t=0.0,
                        S_t=0.0,
                        gps=worker.config.gps,
                        details={"stall_duration_s": round(age_s, 2)},
                    )
                    try:
                        self._alert_queue.put_nowait(tamper_event)
                    except queue.Full:
                        pass
                    tamper_flagged.add(camera_id)

                elif age_s <= HEARTBEAT_TIMEOUT_S and camera_id in tamper_flagged:
                    # Feed recovered
                    logger.info("[Watchdog] Camera '%s' feed recovered", camera_id)
                    tamper_flagged.discard(camera_id)

            self._stop_event.wait(timeout=1.0)  # check every 1s

        logger.info("[Watchdog] Heartbeat monitor stopped")
