"""
SurakshaEdge - Ingest module
Reads video frames and audio chunks, timestamps with monotonic clock.
Supports: video file, webcam index, RTSP URL; mic or WAV for audio.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from queue import Full, Queue
from typing import Optional, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class Frame:
    ts_ns: int          # monotonic nanoseconds at capture
    img: np.ndarray     # BGR uint8, original resolution
    seq: int = 0


@dataclass
class AudioChunk:
    ts_ns: int          # monotonic nanoseconds at capture start
    pcm16k: np.ndarray  # float32, mono, 16 kHz
    seq: int = 0


# ---------------------------------------------------------------------------
# Video ingestor
# ---------------------------------------------------------------------------

class VideoIngest(threading.Thread):
    """Reads frames from file / webcam / RTSP into a bounded queue."""

    RETRY_DELAYS = (1, 2, 4, 8, 16, 30)

    def __init__(
        self,
        source: Union[str, int, Path],
        out_q: Queue,
        fps_limit: Optional[float] = None,
        replay_mode: bool = False,
    ):
        super().__init__(daemon=True, name="VideoIngest")
        self.source = source
        self.out_q = out_q
        self.fps_limit = fps_limit
        self.replay_mode = replay_mode
        self._stop_event = threading.Event()
        self._seq = 0
        self.dropped = 0
        self.captured = 0

    def stop(self):
        self._stop_event.set()

    def _open(self) -> cv2.VideoCapture:
        src = self.source
        if isinstance(src, Path):
            src = str(src)
        cap = cv2.VideoCapture(src)
        if isinstance(src, str) and src.startswith("rtsp"):
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def run(self):
        retry_idx = 0
        cap = None

        # If source is a file path, check existence before entering the retry loop
        src_str = str(self.source)
        if isinstance(self.source, (str, Path)) and not src_str.startswith("rtsp"):
            p = Path(src_str)
            if p.suffix and not p.exists():
                logger.error(
                    "Video file not found: %s — create the file and restart the pipeline.", p
                )
                return  # stop immediately, don't retry

        while not self._stop_event.is_set():
            if cap is None or not cap.isOpened():
                if cap is not None:
                    cap.release()
                    delay = self.RETRY_DELAYS[min(retry_idx, len(self.RETRY_DELAYS) - 1)]
                    logger.warning("STREAM LOST – retrying in %ds", delay)
                    time.sleep(delay)
                    retry_idx += 1
                cap = self._open()
                if not cap.isOpened():
                    logger.error("Cannot open source: %s", self.source)
                    continue
                retry_idx = 0
                # In replay mode, throttle to the video's native FPS so the queue
                # doesn't flood before the vision loop has a chance to process frames.
                if self.replay_mode and self.fps_limit is None:
                    native_fps = cap.get(cv2.CAP_PROP_FPS)
                    if native_fps > 0:
                        self.fps_limit = native_fps
                        logger.info(
                            "Video source opened: %s  (replay at %.1f FPS)", self.source, native_fps
                        )
                    else:
                        logger.info("Video source opened: %s", self.source)
                else:
                    logger.info("Video source opened: %s", self.source)

            ret, img = cap.read()
            if not ret:
                logger.warning("Frame read failed (end of stream or error).")
                cap.release()
                cap = None
                if self.replay_mode:
                    logger.info("Replay complete – stopping ingest.")
                    self._stop_event.set()
                    break
                continue

            ts_ns = time.monotonic_ns()
            frame = Frame(ts_ns=ts_ns, img=img, seq=self._seq)
            self._seq += 1
            self.captured += 1

            if self.replay_mode:
                while not self._stop_event.is_set():
                    try:
                        self.out_q.put(frame, timeout=0.1)
                        break
                    except Full:
                        continue
            else:
                try:
                    self.out_q.put_nowait(frame)
                except Full:
                    # Drop oldest
                    try:
                        self.out_q.get_nowait()
                        self.dropped += 1
                    except Exception:
                        pass
                    try:
                        self.out_q.put_nowait(frame)
                    except Full:
                        self.dropped += 1

            if self.fps_limit:
                time.sleep(1.0 / self.fps_limit)

        if cap is not None:
            cap.release()
        logger.info("VideoIngest stopped. captured=%d dropped=%d", self.captured, self.dropped)


# ---------------------------------------------------------------------------
# Audio ingestor (mic or WAV)
# ---------------------------------------------------------------------------

class AudioIngest(threading.Thread):
    """Reads audio from microphone or WAV file, resamples to 16 kHz mono."""

    CHUNK_S = 0.25  # 250 ms chunks

    def __init__(
        self,
        source: Union[str, int, Path, None],
        out_q: Queue,
        device: Optional[int] = None,
    ):
        super().__init__(daemon=True, name="AudioIngest")
        self.source = source
        self.out_q = out_q
        self.device = device
        self._stop_event = threading.Event()
        self._seq = 0

    def stop(self):
        self._stop_event.set()

    def _resample_to_16k(self, audio: np.ndarray, src_sr: int) -> np.ndarray:
        if src_sr == 16000:
            return audio.astype(np.float32)
        try:
            import librosa
            return librosa.resample(audio.astype(np.float32), orig_sr=src_sr, target_sr=16000)
        except Exception:
            # Simple decimation fallback
            ratio = src_sr / 16000
            indices = np.arange(0, len(audio), ratio).astype(int)
            indices = indices[indices < len(audio)]
            return audio[indices].astype(np.float32)

    def run(self):
        if self.source is None:
            # No audio source configured
            logger.warning("No audio source configured – audio branch disabled.")
            return

        src = self.source
        if isinstance(src, (str, Path)) and Path(str(src)).exists():
            self._run_wav(str(src))
        else:
            self._run_mic()

    def _run_wav(self, path: str):
        import soundfile as sf
        try:
            data, sr = sf.read(path, dtype="float32")
        except Exception as e:
            logger.error("Cannot read WAV %s: %s", path, e)
            return

        if data.ndim > 1:
            data = data.mean(axis=1)
        data = self._resample_to_16k(data, sr)

        chunk_samples = int(self.CHUNK_S * 16000)
        pos = 0
        while pos < len(data) and not self._stop_event.is_set():
            chunk = data[pos: pos + chunk_samples]
            if len(chunk) < chunk_samples:
                chunk = np.pad(chunk, (0, chunk_samples - len(chunk)))
            ts_ns = time.monotonic_ns()
            ac = AudioChunk(ts_ns=ts_ns, pcm16k=chunk, seq=self._seq)
            self._seq += 1
            try:
                self.out_q.put_nowait(ac)
            except Full:
                try:
                    self.out_q.get_nowait()
                except Exception:
                    pass
                try:
                    self.out_q.put_nowait(ac)
                except Full:
                    pass
            pos += chunk_samples
            time.sleep(self.CHUNK_S)

    def _run_mic(self):
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice not installed – mic input unavailable.")
            return

        RATE = 16000
        chunk_samples = int(self.CHUNK_S * RATE)

        def callback(indata, frames, time_info, status):
            if self._stop_event.is_set():
                raise sd.CallbackAbort
            audio = indata[:, 0].copy()
            ts_ns = time.monotonic_ns()
            ac = AudioChunk(ts_ns=ts_ns, pcm16k=audio, seq=self._seq)
            self._seq += 1
            try:
                self.out_q.put_nowait(ac)
            except Full:
                try:
                    self.out_q.get_nowait()
                except Exception:
                    pass
                try:
                    self.out_q.put_nowait(ac)
                except Full:
                    pass

        device_kw = {} if self.device is None else {"device": self.device}
        try:
            with sd.InputStream(
                samplerate=RATE,
                channels=1,
                dtype="float32",
                blocksize=chunk_samples,
                callback=callback,
                **device_kw,
            ):
                while not self._stop_event.is_set():
                    time.sleep(0.1)
        except Exception as e:
            logger.error("Mic stream error: %s", e)
