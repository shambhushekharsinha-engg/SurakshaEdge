"""
Generate realistic synthetic audio training data for SurakshaEdge audio CNN.

Generates:
  20 scream-like WAVs → data/audio/scream/
  20 negative WAVs  → data/audio/negative/
     (crowd noise, clapping, music chord, pink noise)

Usage:
    python scripts/gen_synthetic_audio.py
"""
from pathlib import Path

import numpy as np
import soundfile as sf

SAMPLE_RATE = 16000
rng = np.random.default_rng(42)

Path("data/audio/scream").mkdir(parents=True, exist_ok=True)
Path("data/audio/negative").mkdir(parents=True, exist_ok=True)


def make_scream(idx: int) -> np.ndarray:
    """
    High-energy frequency-modulated burst with harmonics and noise onset.
    Mimics a human scream: fast attack, sustained mid-section, tail off.
    """
    dur = rng.uniform(1.0, 2.5)
    n = int(dur * SAMPLE_RATE)
    t = np.linspace(0, dur, n, endpoint=False, dtype=np.float32)

    # Base frequency sweep: 400 → 1200 → 600 Hz
    f_center = rng.uniform(600, 1000)
    f_sweep = np.interp(t, [0, dur * 0.3, dur], [400.0, f_center + 300, 600.0]).astype(np.float32)

    # Vibrato: ±50 Hz at 6 Hz
    vibrato = 50.0 * np.sin(2 * np.pi * 6.0 * t).astype(np.float32)
    freq = f_sweep + vibrato

    # Phase accumulation for frequency modulation
    phase = np.cumsum(2 * np.pi * freq / SAMPLE_RATE).astype(np.float32)
    sig = np.sin(phase).astype(np.float32)

    # Add harmonics (2nd and 3rd at reduced amp)
    sig += 0.35 * np.sin(2 * phase)
    sig += 0.15 * np.sin(3 * phase)

    # Amplitude envelope: fast attack 0.05s, sustain, decay 0.2s
    env = np.ones(n, dtype=np.float32)
    attack = int(0.05 * SAMPLE_RATE)
    decay = int(0.2 * SAMPLE_RATE)
    env[:attack] = np.linspace(0, 1, attack)
    env[n - decay :] = np.linspace(1, 0, decay)
    sig *= env

    # Noise burst at onset (adds breathiness)
    noise_len = min(int(0.15 * SAMPLE_RATE), n)
    sig[:noise_len] += 0.3 * rng.standard_normal(noise_len).astype(np.float32)

    # Normalize
    sig /= np.abs(sig).max() + 1e-6
    return sig


def make_crowd(idx: int) -> np.ndarray:
    """Many overlapping low-frequency voices + broadband noise."""
    dur = rng.uniform(1.5, 3.0)
    n = int(dur * SAMPLE_RATE)
    t = np.linspace(0, dur, n, dtype=np.float32)
    sig = np.zeros(n, dtype=np.float32)
    for _ in range(20):
        f = rng.uniform(80, 400)
        phase_off = rng.uniform(0, 2 * np.pi)
        amp = rng.uniform(0.03, 0.12)
        sig += amp * np.sin(2 * np.pi * f * t + phase_off)
    sig += 0.15 * rng.standard_normal(n).astype(np.float32)
    sig /= np.abs(sig).max() + 1e-6
    sig *= 0.5  # crowd is not very loud
    return sig.astype(np.float32)


def make_clapping(idx: int) -> np.ndarray:
    """Periodic broadband impulse bursts at 2–4 Hz."""
    dur = rng.uniform(1.5, 3.0)
    n = int(dur * SAMPLE_RATE)
    sig = np.zeros(n, dtype=np.float32)
    rate = rng.uniform(2.0, 4.0)
    clap_period = int(SAMPLE_RATE / rate)
    clap_len = int(0.05 * SAMPLE_RATE)
    pos = 0
    while pos < n:
        end = min(pos + clap_len, n)
        impulse = rng.standard_normal(end - pos).astype(np.float32)
        # Exponential decay of the clap
        decay = np.exp(-np.linspace(0, 15, end - pos)).astype(np.float32)
        sig[pos:end] += 0.7 * impulse * decay
        pos += clap_period + rng.integers(-int(clap_period * 0.1), int(clap_period * 0.1) + 1)
    sig /= np.abs(sig).max() + 1e-6
    sig *= 0.6
    return sig


def make_music(idx: int) -> np.ndarray:
    """Music-like: three harmonically related sine waves (chord)."""
    dur = rng.uniform(1.5, 3.0)
    n = int(dur * SAMPLE_RATE)
    t = np.linspace(0, dur, n, dtype=np.float32)
    root = rng.uniform(220, 440)
    sig = (
        0.4 * np.sin(2 * np.pi * root * t)
        + 0.3 * np.sin(2 * np.pi * root * 1.25 * t)  # major third
        + 0.25 * np.sin(2 * np.pi * root * 1.5 * t)  # perfect fifth
    ).astype(np.float32)
    # Gentle AM modulation (tremolo)
    sig *= (0.8 + 0.2 * np.sin(2 * np.pi * 3.5 * t)).astype(np.float32)
    sig /= np.abs(sig).max() + 1e-6
    sig *= 0.4  # music is quieter
    return sig


def make_pink_noise(idx: int) -> np.ndarray:
    """1/f (pink) noise via scipy — background ambience."""
    from scipy.signal import lfilter
    dur = rng.uniform(1.5, 3.0)
    n = int(dur * SAMPLE_RATE)
    white = rng.standard_normal(n).astype(np.float32)
    # Simple 1/f approximation: low-pass-ish filter on white noise
    b = np.array([0.049922035, -0.095993537, 0.050612699, -0.004408786], dtype=np.float32)
    a = np.array([1, -2.494956002, 2.017265875, -0.522189400], dtype=np.float32)
    pink = lfilter(b, a, white).astype(np.float32)
    pink /= np.abs(pink).max() + 1e-6
    pink *= 0.3
    return pink


# ── Generate 20 screams ────────────────────────────────────────────────────
for i in range(20):
    sig = make_scream(i)
    sf.write(f"data/audio/scream/synth_scream_{i:02d}.wav", sig, SAMPLE_RATE)

# ── Generate 20 negatives (5 each type) ────────────────────────────────────
generators = [make_crowd, make_clapping, make_music, make_pink_noise]
for gi, gen_fn in enumerate(generators):
    for j in range(5):
        idx = gi * 5 + j
        sig = gen_fn(idx)
        sf.write(f"data/audio/negative/synth_neg_{idx:02d}.wav", sig, SAMPLE_RATE)

scream_count = len(list(Path("data/audio/scream").glob("*.wav")))
neg_count = len(list(Path("data/audio/negative").glob("*.wav")))
print(f"Synthetic audio generated: {scream_count} screams, {neg_count} negatives")
print("NOTE: Synthetic data — replace with real recordings for production.")
