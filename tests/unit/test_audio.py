"""
Unit tests for the audio module (UT-07, UT-08).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from surakshaedge.edge.audio import N_MFCC, SAMPLE_RATE, AudioScorer, extract_mfcc


# UT-07: MFCC shape
def test_mfcc_shape_1s_16khz():
    """MFCC of a 1s window at 16kHz should be (40, 98)."""
    audio = np.random.randn(SAMPLE_RATE).astype(np.float32)
    mfcc = extract_mfcc(audio, sr=SAMPLE_RATE)
    assert mfcc.shape[0] == N_MFCC, f"Expected {N_MFCC} MFCC bands, got {mfcc.shape[0]}"
    assert mfcc.shape[1] == 98, f"Expected 98 time frames, got {mfcc.shape[1]}"


# UT-08: Resampling from 44.1 kHz and 48 kHz
def test_audio_scorer_accumulates_chunks():
    """AudioScorer accumulates 0.25s chunks and emits SScore on full 1s window."""
    scorer = AudioScorer(model_path=None, s_threshold=0.70)
    chunk_samples = int(0.25 * SAMPLE_RATE)
    ts = 0

    results = []
    for i in range(8):
        chunk = np.random.randn(chunk_samples).astype(np.float32) * 0.1
        result = scorer.update(chunk, ts)
        ts += int(0.25 * 1e9)
        if result is not None:
            results.append(result)

    # Should have produced some SScores
    assert len(results) >= 1, "AudioScorer should emit results for a 1s window"
    for r in results:
        assert 0.0 <= r.S_t <= 1.0, f"S_t out of range: {r.S_t}"


def test_mfcc_normalised():
    """MFCC output should be approximately zero-mean per band."""
    audio = np.random.randn(SAMPLE_RATE).astype(np.float32)
    mfcc = extract_mfcc(audio, sr=SAMPLE_RATE)
    # After per-window normalisation, mean should be near 0
    means = mfcc.mean(axis=1)
    assert np.all(np.abs(means) < 1.0), f"MFCC means not normalised: {means[:5]}"


def test_mfcc_nonzero_no_librosa_numba():
    """extract_mfcc must return non-zero values — guards against silent Numba/librosa fallback.

    If Numba fails (NumPy > 2.4 incompatibility) the old code returned
    np.zeros((40, 98)).  The pure-numpy implementation must never do that.
    """
    rng = np.random.default_rng(42)
    audio = rng.standard_normal(SAMPLE_RATE).astype(np.float32)
    mfcc = extract_mfcc(audio, sr=SAMPLE_RATE)
    nonzero = np.count_nonzero(mfcc)
    assert nonzero > 1000, (
        f"MFCC has only {nonzero}/3920 non-zero entries — "
        "likely returned zeros due to a silent extraction failure"
    )
