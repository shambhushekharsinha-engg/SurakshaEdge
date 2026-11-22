"""
SurakshaEdge - Kinematics module
Computes K_t = 0.4*V_w + 0.3*A_j + 0.3*Q_p from track history.

V_w: normalized wrist speed (torso-lengths per second), entropy-adjusted.
A_j: limb angular velocity (normalised)
Q_p: close-contact flag (IoU + closing velocity)

Trajectory entropy adjustment: V_w is modulated by FFT-based spectral entropy
of the wrist trajectory. Rhythmic (low-entropy) motion suppresses V_w;
chaotic (high-entropy) motion amplifies V_w toward its full value.
"""
from __future__ import annotations

import collections
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from .pose import CONF_THRESH, KP, MIN_TORSO_PX, Track

logger = logging.getLogger(__name__)

SMOOTH_ALPHA = 0.5   # EMA alpha for keypoint smoothing
MEDIAN_WINDOW = 5    # frames for K_t median smoothing

# K_t weights
W_VW = 0.4
W_AJ = 0.3
W_QP = 0.3

# Vision flag parameters
K_THRESHOLD = 0.62
K_PERSIST_S = 0.4   # K_t must be above threshold for this many seconds


@dataclass
class KScore:
    ts_ns: int
    K_t: float
    V_w: float
    A_j: float
    Q_p: float
    track_ids: List[int] = field(default_factory=list)


class KinematicsEngine:
    """
    Stateful kinematic scorer. Call update() with each frame's tracks.
    """

    def __init__(
        self,
        weights: Optional[dict] = None,
        k_threshold: float = K_THRESHOLD,
        k_persist_s: float = K_PERSIST_S,
    ):
        self.k_threshold = k_threshold
        self.k_persist_s = k_persist_s
        if weights:
            self.w_vw = weights.get("V_w", W_VW)
            self.w_aj = weights.get("A_j", W_AJ)
            self.w_qp = weights.get("Q_p", W_QP)
        else:
            self.w_vw, self.w_aj, self.w_qp = W_VW, W_AJ, W_QP

        # Per-track state: track_id -> {"kp": smoothed keypoints, "ts_ns": last ts}
        self._track_state: Dict[int, dict] = {}
        # Per-track wrist position history for entropy computation: track_id -> deque of (lw_xy, rw_xy)
        self._wrist_history: Dict[int, collections.deque] = {}
        # Last few K_t values for median smoothing
        self._kt_history: collections.deque = collections.deque(maxlen=MEDIAN_WINDOW)
        # Flag state
        self._flag_start_ns: Optional[int] = None
        self._flag: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, tracks: List[Track], ts_ns: int) -> KScore:
        # Clean stale tracks (not seen for > 1 s)
        self._prune_stale(ts_ns)

        scores_per_track = []
        V_w_max = 0.0
        A_j_max = 0.0
        Q_p = 0.0

        for track in tracks:
            kp = self._smooth_keypoints(track)
            if kp is None:
                continue
            torso_len = self._torso_length(kp)
            if torso_len < MIN_TORSO_PX:
                continue

            prev = self._track_state.get(track.track_id)
            self._track_state[track.track_id] = {"kp": kp, "ts_ns": ts_ns}

            # Record wrist positions for entropy
            lw = kp[KP["left_wrist"], :2]
            rw = kp[KP["right_wrist"], :2]
            if track.track_id not in self._wrist_history:
                self._wrist_history[track.track_id] = collections.deque(maxlen=30)
            self._wrist_history[track.track_id].append((lw.copy(), rw.copy()))

            if prev is None:
                continue  # Need two frames to compute velocity

            dt_s = (ts_ns - prev["ts_ns"]) / 1e9
            if dt_s <= 0:
                continue
            prev_kp = prev["kp"]

            vw = self._wrist_speed(kp, prev_kp, dt_s, torso_len)
            aj = self._limb_angular_velocity(kp, prev_kp, dt_s)

            # Apply trajectory entropy adjustment: chaotic motion → full V_w,
            # rhythmic/sports motion → suppressed V_w.
            wrist_hist = list(self._wrist_history.get(track.track_id, []))
            entropy = self._trajectory_entropy(track.track_id, wrist_hist)
            vw_adjusted = vw * (0.5 + 0.5 * entropy)

            V_w_max = max(V_w_max, vw_adjusted)
            A_j_max = max(A_j_max, aj)
            scores_per_track.append(track.track_id)

        # Contact flag: check all pairs
        track_list = [t for t in tracks if self._track_state.get(t.track_id) is not None]
        Q_p = self._contact_flag(track_list, ts_ns)

        K_t_raw = self.w_vw * V_w_max + self.w_aj * A_j_max + self.w_qp * Q_p
        K_t_raw = float(np.clip(K_t_raw, 0.0, 1.0))

        # Smooth with median
        self._kt_history.append(K_t_raw)
        K_t = float(np.median(list(self._kt_history)))

        # Update persistence flag
        self._update_flag(K_t, ts_ns)

        return KScore(
            ts_ns=ts_ns,
            K_t=K_t,
            V_w=V_w_max,
            A_j=A_j_max,
            Q_p=Q_p,
            track_ids=scores_per_track,
        )

    @property
    def flag(self) -> bool:
        return self._flag

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _smooth_keypoints(self, track: Track) -> Optional[np.ndarray]:
        """EMA smoothing on keypoint (x,y). Returns None if torso invalid."""
        kp = track.keypoints.copy()  # (17, 3)
        prev_state = self._track_state.get(track.track_id)
        if prev_state is not None:
            prev_kp = prev_state["kp"]
            for i in range(17):
                if kp[i, 2] >= CONF_THRESH and prev_kp[i, 2] >= CONF_THRESH:
                    kp[i, :2] = SMOOTH_ALPHA * kp[i, :2] + (1 - SMOOTH_ALPHA) * prev_kp[i, :2]
                elif kp[i, 2] < CONF_THRESH:
                    kp[i] = prev_kp[i]  # keep old value
        # Mask low-confidence keypoints as NaN
        mask = kp[:, 2] < CONF_THRESH
        kp[mask, :2] = np.nan
        return kp

    def _torso_length(self, kp: np.ndarray) -> float:
        ls, rs = kp[KP["left_shoulder"], :2], kp[KP["right_shoulder"], :2]
        lh, rh = kp[KP["left_hip"], :2], kp[KP["right_hip"], :2]
        # Compute midpoints manually to avoid RuntimeWarning: Mean of empty slice
        # when both points are NaN (zero-confidence keypoints).
        def _midpoint(a: np.ndarray, b: np.ndarray) -> np.ndarray:
            a_nan = np.any(np.isnan(a))
            b_nan = np.any(np.isnan(b))
            if a_nan and b_nan:
                return np.array([np.nan, np.nan])
            if a_nan:
                return b.copy()
            if b_nan:
                return a.copy()
            return (a + b) / 2.0
        shoulder_mid = _midpoint(ls, rs)
        hip_mid = _midpoint(lh, rh)
        if np.any(np.isnan(shoulder_mid)) or np.any(np.isnan(hip_mid)):
            return 0.0
        return float(np.linalg.norm(shoulder_mid - hip_mid))

    def _wrist_speed(self, kp: np.ndarray, prev_kp: np.ndarray, dt_s: float, torso_len: float) -> float:
        v_max = 0.0
        for wrist_idx in [KP["left_wrist"], KP["right_wrist"]]:
            p_cur = kp[wrist_idx, :2]
            p_prev = prev_kp[wrist_idx, :2]
            if np.any(np.isnan(p_cur)) or np.any(np.isnan(p_prev)):
                continue
            speed = np.linalg.norm(p_cur - p_prev) / (dt_s * torso_len + 1e-6)
            v_max = max(v_max, speed)
        return float(np.clip(v_max / 3.0, 0.0, 1.0))

    def _limb_angular_velocity(self, kp: np.ndarray, prev_kp: np.ndarray, dt_s: float) -> float:
        omega_max = 0.0
        limbs = [
            (KP["left_shoulder"], KP["left_elbow"], KP["left_wrist"]),
            (KP["right_shoulder"], KP["right_elbow"], KP["right_wrist"]),
        ]
        for s, e, w in limbs:
            for kp_cur, kp_pr in [(kp, prev_kp)]:
                p_s = kp_cur[s, :2]; p_e = kp_cur[e, :2]; p_w = kp_cur[w, :2]
                if np.any(np.isnan([p_s, p_e, p_w])):
                    continue
                p_s_p = kp_pr[s, :2]; p_e_p = kp_pr[e, :2]; p_w_p = kp_pr[w, :2]
                if np.any(np.isnan([p_s_p, p_e_p, p_w_p])):
                    continue
                theta_cur = self._angle(p_s, p_e, p_w)
                theta_prev = self._angle(p_s_p, p_e_p, p_w_p)
                if theta_cur is None or theta_prev is None:
                    continue
                omega = abs(theta_cur - theta_prev) / (dt_s + 1e-6)
                omega_max = max(omega_max, omega)
        return float(np.clip(omega_max / 12.0, 0.0, 1.0))

    @staticmethod
    def _angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> Optional[float]:
        """Angle at vertex b in triangle a-b-c (radians)."""
        v1 = a - b; v2 = c - b
        n1 = np.linalg.norm(v1); n2 = np.linalg.norm(v2)
        if n1 < 1e-6 or n2 < 1e-6:
            return None
        cos_val = np.dot(v1, v2) / (n1 * n2)
        cos_val = np.clip(cos_val, -1.0, 1.0)
        return float(np.arccos(cos_val))

    def _contact_flag(self, tracks: List[Track], ts_ns: int) -> float:
        """Q_p = 1 if any pair has IoU > 0.15 and is closing faster than 0.5 L/s."""
        if len(tracks) < 2:
            return 0.0
        for i in range(len(tracks)):
            for j in range(i + 1, len(tracks)):
                t1, t2 = tracks[i], tracks[j]
                iou = self._bbox_iou(t1.bbox, t2.bbox)
                if iou > 0.15:
                    return 1.0
                # Check closing velocity
                c1 = np.array([(t1.bbox[0]+t1.bbox[2])/2, (t1.bbox[1]+t1.bbox[3])/2])
                c2 = np.array([(t2.bbox[0]+t2.bbox[2])/2, (t2.bbox[1]+t2.bbox[3])/2])
                dist = np.linalg.norm(c1 - c2)
                p1 = self._track_state.get(t1.track_id)
                p2 = self._track_state.get(t2.track_id)
                if p1 and p2:
                    prev_c1 = np.array([(p1["kp"][KP["left_hip"],0]+p1["kp"][KP["right_hip"],0])/2,
                                        (p1["kp"][KP["left_hip"],1]+p1["kp"][KP["right_hip"],1])/2])
                    prev_c2 = np.array([(p2["kp"][KP["left_hip"],0]+p2["kp"][KP["right_hip"],0])/2,
                                        (p2["kp"][KP["left_hip"],1]+p2["kp"][KP["right_hip"],1])/2])
                    if not np.any(np.isnan([prev_c1, prev_c2])):
                        prev_dist = np.linalg.norm(prev_c1 - prev_c2)
                        dt_s = (ts_ns - max(p1["ts_ns"], p2["ts_ns"])) / 1e9
                        # torso estimate: half of current dist
                        L_est = max(dist / 2.0, 50.0)
                        closing_rate = (prev_dist - dist) / (dt_s * L_est + 1e-6)
                        if closing_rate > 0.5:
                            return 1.0
        return 0.0

    @staticmethod
    def _bbox_iou(b1: np.ndarray, b2: np.ndarray) -> float:
        ix1 = max(b1[0], b2[0]); iy1 = max(b1[1], b2[1])
        ix2 = min(b1[2], b2[2]); iy2 = min(b1[3], b2[3])
        iw = max(0, ix2 - ix1); ih = max(0, iy2 - iy1)
        inter = iw * ih
        a1 = (b1[2]-b1[0]) * (b1[3]-b1[1])
        a2 = (b2[2]-b2[0]) * (b2[3]-b2[1])
        union = a1 + a2 - inter + 1e-6
        return inter / union

    def _update_flag(self, K_t: float, ts_ns: int):
        if K_t >= self.k_threshold:
            if self._flag_start_ns is None:
                self._flag_start_ns = ts_ns
            elapsed_s = (ts_ns - self._flag_start_ns) / 1e9
            if elapsed_s >= self.k_persist_s:
                self._flag = True
        else:
            self._flag_start_ns = None
            self._flag = False

    def _prune_stale(self, ts_ns: int, max_age_ns: int = 2_000_000_000):
        stale = [tid for tid, st in self._track_state.items()
                 if (ts_ns - st["ts_ns"]) > max_age_ns]
        for tid in stale:
            del self._track_state[tid]
            self._wrist_history.pop(tid, None)

    def _trajectory_entropy(self, track_id: int, kp_history: list) -> float:
        """
        Compute FFT-based spectral entropy of wrist trajectory over last 30 frames.
        Rhythmic motion (sports ~2-4 Hz) → low entropy → suppresses V_w contribution.
        Chaotic struggle → high entropy → amplifies V_w contribution.
        Returns: entropy scalar [0.0, 1.0]
        """
        if len(kp_history) < 5:
            return 0.5

        N = min(30, len(kp_history))
        frames = kp_history[-N:]

        # Collect wrist X/Y positions (use left wrist; fallback right if NaN)
        xs = []
        ys = []
        for entry in frames:
            lw, rw = entry  # each is a 2-element array [x, y]
            if not np.any(np.isnan(lw)):
                xs.append(lw[0])
                ys.append(lw[1])
            elif not np.any(np.isnan(rw)):
                xs.append(rw[0])
                ys.append(rw[1])
            else:
                xs.append(0.0)
                ys.append(0.0)

        xs = np.array(xs, dtype=float)
        ys = np.array(ys, dtype=float)

        # Compute PSD via FFT for X and Y, combine
        fft_x = np.fft.rfft(xs - xs.mean())
        fft_y = np.fft.rfft(ys - ys.mean())
        psd = np.abs(fft_x) ** 2 + np.abs(fft_y) ** 2

        total = psd.sum()
        if total < 1e-12:
            return 0.5  # no motion → neutral

        p = psd / total
        # Shannon entropy
        raw_entropy = -np.sum(p * np.log2(p + 1e-9))

        # Normalise to [0, 1]
        max_entropy = np.log2(len(p))
        if max_entropy < 1e-12:
            return 0.5

        entropy = float(np.clip(raw_entropy / max_entropy, 0.0, 1.0))
        return entropy
