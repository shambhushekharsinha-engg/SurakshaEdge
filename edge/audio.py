"""
SurakshaEdge - Audio model module
MFCC feature extraction + ONNX-based MFCC-CNN scream classifier.
Falls back to a pretrained AudioSet/YAMNet-like baseline if available.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
WINDOW_S = 1.0
HOP_S = 0.25
N_MFCC = 40
N_FFT = 512
WIN_SAMPLES = 400   # 25 ms
HOP_SAMPLES = 160   # 10 ms


@dataclass
class SScore:
    ts_ns: int
    S_t: float      # scream probability [0, 1]


def extract_mfcc(pcm: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """
    Extract 40 MFCC coefficients from a 1 s audio window.
    Returns shape (40, 98).

    Implemented with scipy + pure numpy to avoid librosa's Numba JIT,
    which fails on NumPy >= 2.5 (Numba 0.61 / librosa 0.11 constraint).
    The algorithm matches librosa's default pipeline:
      short-time FFT → mel filterbank → log → DCT (type-II) → first N_MFCC rows.
    """
    try:
        from scipy.signal import get_window
        from scipy.fft import fft, dct

        # --- STFT power spectrum ---
        window = get_window("hann", WIN_SAMPLES, fftbins=True).astype(np.float32)
        n_frames = 1 + (len(pcm) - WIN_SAMPLES) // HOP_SAMPLES
        # Pad if short
        pcm_f = pcm.astype(np.float32)
        pad_len = WIN_SAMPLES + (n_frames - 1) * HOP_SAMPLES - len(pcm_f)
        if pad_len > 0:
            pcm_f = np.pad(pcm_f, (0, pad_len))

        frames = np.stack(
            [pcm_f[i * HOP_SAMPLES: i * HOP_SAMPLES + WIN_SAMPLES] * window
             for i in range(n_frames)],
            axis=0,
        )  # (n_frames, WIN_SAMPLES)

        # Zero-pad to N_FFT for frequency resolution
        if N_FFT > WIN_SAMPLES:
            frames = np.pad(frames, ((0, 0), (0, N_FFT - WIN_SAMPLES)))

        spec = np.abs(fft(frames, n=N_FFT, axis=1)[:, : N_FFT // 2 + 1]) ** 2  # power

        # --- Mel filterbank (Hz → mel, triangular filters) ---
        n_mels = 40
        f_min, f_max = 0.0, float(sr) / 2.0
        mel_min = 2595.0 * np.log10(1.0 + f_min / 700.0)
        mel_max = 2595.0 * np.log10(1.0 + f_max / 700.0)
        mel_pts = np.linspace(mel_min, mel_max, n_mels + 2)
        hz_pts = 700.0 * (10.0 ** (mel_pts / 2595.0) - 1.0)
        bin_pts = np.floor((N_FFT + 1) * hz_pts / sr).astype(int)

        n_freq = N_FFT // 2 + 1
        fbank = np.zeros((n_mels, n_freq), dtype=np.float32)
        for m in range(1, n_mels + 1):
            lo, ctr, hi = bin_pts[m - 1], bin_pts[m], bin_pts[m + 1]
            for k in range(lo, ctr):
                if ctr != lo:
                    fbank[m - 1, k] = (k - lo) / (ctr - lo)
            for k in range(ctr, hi):
                if hi != ctr:
                    fbank[m - 1, k] = (hi - k) / (hi - ctr)

        mel_spec = np.dot(spec, fbank.T)  # (n_frames, n_mels)
        mel_spec = np.log(mel_spec + 1e-9)

        # --- DCT-II to get MFCCs, keep first N_MFCC ---
        mfcc_raw = dct(mel_spec, type=2, axis=1, norm="ortho")  # (n_frames, n_mels)
        mfcc = mfcc_raw[:, :N_MFCC].T  # (N_MFCC, n_frames)

        # Ensure exactly 98 time frames (pad or trim)
        target_frames = 98
        if mfcc.shape[1] < target_frames:
            mfcc = np.pad(mfcc, ((0, 0), (0, target_frames - mfcc.shape[1])))
        else:
            mfcc = mfcc[:, :target_frames]

        # Per-window mean/variance normalisation
        mean = mfcc.mean(axis=1, keepdims=True)
        std = mfcc.std(axis=1, keepdims=True) + 1e-6
        return ((mfcc - mean) / std).astype(np.float32)

    except Exception as e:
        logger.error("MFCC extraction failed: %s", e)
        return np.zeros((N_MFCC, 98), dtype=np.float32)


class AudioScorer:
    """
    Wraps the ONNX MFCC-CNN model. Accumulates 0.25 s audio chunks,
    runs inference on every 1 s window (with 0.25 s hop), emits SScore.
    Falls back to a simple energy-based heuristic if no model is found.

    IMPORTANT: Check `scorer.mode` before trusting S_t scores:
        "mfcc_cnn"       — trained model loaded, S_t is a real scream probability
        "energy_fallback" — no model; S_t responds to ANY loud sound (not scream-specific)
    Label "energy fallback" clearly on any demo or slide that uses this mode.
    """

    S_THRESHOLD = 0.70

    def __init__(self, model_path: Optional[str] = None, s_threshold: float = S_THRESHOLD):
        self.s_threshold = s_threshold
        self._model = None
        self._session = None
        self._buffer: np.ndarray = np.zeros(0, dtype=np.float32)
        self._window_samples = int(WINDOW_S * SAMPLE_RATE)
        self._hop_samples = int(HOP_S * SAMPLE_RATE)
        self._flag = False
        self.mode: str = "energy_fallback"   # updated on successful ONNX load

        if model_path:
            self._load_onnx(model_path)

    def _load_onnx(self, path: str):
        try:
            import onnxruntime as ort
            # Prefer CPU-only to avoid spurious CUDA UserWarning on machines without GPU
            providers = ["CPUExecutionProvider"]
            self._session = ort.InferenceSession(path, providers=providers)
            self._input_name = self._session.get_inputs()[0].name
            self.mode = "mfcc_cnn"
            logger.info("ONNX audio model loaded: %s  mode=mfcc_cnn", path)
        except Exception as e:
            logger.warning("Could not load ONNX audio model: %s. Using energy_fallback.", e)
            self._session = None
            self.mode = "energy_fallback"

    def update(self, chunk: np.ndarray, ts_ns: int) -> Optional[SScore]:
        """
        Feed a 0.25 s chunk. Returns SScore when a full 1 s window is available.
        """
        self._buffer = np.concatenate([self._buffer, chunk])
        result = None

        while len(self._buffer) >= self._window_samples:
            window = self._buffer[:self._window_samples]
            S_t = self._score_window(window, ts_ns)
            # Use window-centre time for gate alignment
            centre_offset_ns = int(WINDOW_S / 2 * 1e9)
            score = SScore(ts_ns=ts_ns - centre_offset_ns, S_t=S_t)
            result = score
            self._flag = S_t >= self.s_threshold
            self._buffer = self._buffer[self._hop_samples:]

        return result

    @property
    def flag(self) -> bool:
        return self._flag

    def _score_window(self, window: np.ndarray, ts_ns: int) -> float:
        if self._session is not None:
            return self._score_onnx(window)
        return self._score_fallback(window)

    def _score_onnx(self, window: np.ndarray) -> float:
        mfcc = extract_mfcc(window)          # (40, 98)
        inp = mfcc[np.newaxis, np.newaxis]   # (1, 1, 40, 98)
        try:
            out = self._session.run(None, {self._input_name: inp})
            return float(np.clip(out[0].squeeze(), 0.0, 1.0))
        except Exception as e:
            logger.error("ONNX inference error: %s", e)
            return 0.0

    def _score_fallback(self, window: np.ndarray) -> float:
        """
        Energy + zero-crossing heuristic. Approximate substitute until model is ready.
        Not a real scream detector – used for smoke-testing the pipeline.
        """
        rms = float(np.sqrt(np.mean(window ** 2)))
        zcr = float(np.mean(np.abs(np.diff(np.sign(window)))) / 2)
        # Very rough heuristic: loud + high ZCR = scream-like
        energy_score = np.clip(rms * 10, 0, 1)
        zcr_score = np.clip(zcr * 5, 0, 1)
        return float(0.6 * energy_score + 0.4 * zcr_score)
