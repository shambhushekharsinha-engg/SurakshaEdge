"""
SurakshaEdge - Audio CNN model definition and training
Binary classifier: scream/vocal distress vs. everything else.
Input: (batch, 1, 40, 98) MFCC tensor
Output: (batch, 1) sigmoid probability

Training:
    python training/audio_cnn/train.py --data-dir data/audio --output models/audio_cnn.onnx

Exports ONNX after training for use with onnxruntime in edge/audio.py.
"""
from __future__ import annotations

import argparse
import logging
import os
import time
import warnings
from pathlib import Path
from typing import List, Optional, Tuple

# Suppress PyTorch ONNX legacy-exporter DeprecationWarning (torch >= 2.9).
# We intentionally use dynamo=False to avoid requiring onnxscript.
warnings.filterwarnings(
    "ignore",
    message="You are using the legacy TorchScript-based ONNX export",
    category=DeprecationWarning,
)

import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ---------------------------------------------------------------------------
# Model definition
# ---------------------------------------------------------------------------

def build_model():
    """Three conv blocks + global pool + dense. Returns nn.Module."""
    try:
        import torch
        import torch.nn as nn

        class AudioCNN(nn.Module):
            def __init__(self):
                super().__init__()
                self.features = nn.Sequential(
                    # Block 1: (1, 40, 98) → (16, 20, 49)
                    nn.Conv2d(1, 16, kernel_size=3, padding=1), nn.BatchNorm2d(16), nn.ReLU(),
                    nn.MaxPool2d(2),
                    # Block 2: (16, 20, 49) → (32, 10, 24)
                    nn.Conv2d(16, 32, kernel_size=3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
                    nn.MaxPool2d(2),
                    # Block 3: (32, 10, 24) → (64, 5, 12)
                    nn.Conv2d(32, 64, kernel_size=3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
                    nn.MaxPool2d(2),
                )
                self.classifier = nn.Sequential(
                    nn.AdaptiveAvgPool2d(1),   # Global average pool → (64, 1, 1)
                    nn.Flatten(),
                    nn.Linear(64, 64),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(64, 1),
                    nn.Sigmoid(),
                )

            def forward(self, x):
                return self.classifier(self.features(x))

        return AudioCNN()
    except ImportError as e:
        raise ImportError("PyTorch not available. Install with: pip install torch") from e


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

def load_dataset(data_dir: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Expects data_dir/ with two subdirs:
        scream/   — positive WAV files
        negative/ — hard negative WAV files
    Returns (X, y) where X is (N, 1, 40, 98) float32, y is (N,) float32.
    """
    import soundfile as sf
    from surakshaedge.edge.audio import extract_mfcc, SAMPLE_RATE

    X, y = [], []
    data_path = Path(data_dir)
    WINDOW = SAMPLE_RATE  # 1 s

    for label_name, label_val in [("scream", 1.0), ("negative", 0.0)]:
        subdir = data_path / label_name
        if not subdir.exists():
            logger.warning("Data dir not found: %s", subdir)
            continue
        for wav_file in subdir.glob("*.wav"):
            try:
                data, sr = sf.read(str(wav_file), dtype="float32")
                if data.ndim > 1:
                    data = data.mean(axis=1)
                # Resample to 16 kHz if needed
                if sr != SAMPLE_RATE:
                    try:
                        import librosa
                        data = librosa.resample(data, orig_sr=sr, target_sr=SAMPLE_RATE)
                    except Exception:
                        pass

                # Sliding windows with 0.25 s hop
                hop = SAMPLE_RATE // 4
                for start in range(0, max(1, len(data) - WINDOW + 1), hop):
                    window = data[start: start + WINDOW]
                    if len(window) < WINDOW:
                        window = np.pad(window, (0, WINDOW - len(window)))
                    mfcc = extract_mfcc(window, sr=SAMPLE_RATE)   # (40, 98)
                    X.append(mfcc[np.newaxis])  # (1, 40, 98)
                    y.append(label_val)
            except Exception as e:
                logger.warning("Could not load %s: %s", wav_file, e)

    if not X:
        raise ValueError(f"No audio data found in {data_dir}. Expected scream/ and negative/ subdirs.")

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(data_dir: str, output_path: str, epochs: int = 30, batch_size: int = 64, lr: float = 1e-3):
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset, random_split

    logger.info("Loading dataset from %s", data_dir)
    X, y = load_dataset(data_dir)
    logger.info("Dataset: %d samples (%.0f%% positive)", len(y), y.mean() * 100)

    # Class weights for imbalanced data
    pos_weight = torch.tensor([(y == 0.0).sum() / max((y == 1.0).sum(), 1)], dtype=torch.float32)
    logger.info("Class pos_weight: %.2f", pos_weight.item())

    X_t = torch.from_numpy(X)
    y_t = torch.from_numpy(y).unsqueeze(1)

    dataset = TensorDataset(X_t, y_t)
    val_size = max(1, int(0.2 * len(dataset)))
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training on %s", device)

    model = build_model().to(device)
    criterion = nn.BCELoss(weight=pos_weight.to(device))
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)

    best_auc = 0.0
    best_state = None

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            # SpecAugment (simple time + frequency masking)
            xb = _spec_augment(xb)
            optimizer.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        # Validation
        model.eval()
        val_probs, val_labels = [], []
        with torch.no_grad():
            for xb, yb in val_loader:
                out = model(xb.to(device))
                val_probs.extend(out.cpu().squeeze().tolist())
                val_labels.extend(yb.squeeze().tolist())

        from sklearn.metrics import roc_auc_score
        try:
            auc = roc_auc_score(val_labels, val_probs)
        except Exception:
            auc = 0.5

        scheduler.step(-auc)
        logger.info("Epoch %2d/%d  loss=%.4f  val_AUC=%.4f", epoch, epochs, train_loss / len(train_loader), auc)

        if auc > best_auc:
            best_auc = auc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

    # Load best weights
    if best_state:
        model.load_state_dict(best_state)

    logger.info("Best validation AUC: %.4f", best_auc)

    # Export to ONNX using the legacy (TorchScript-based) exporter.
    # torch 2.x defaults to the dynamo exporter which requires `onnxscript`;
    # passing dynamo=False forces the old path that only needs `onnx`.
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    model.cpu().eval()
    dummy = torch.randn(1, 1, 40, 98)
    try:
        # torch >= 2.1 legacy path
        torch.onnx.export(
            model, dummy,
            output_path,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
            opset_version=14,
            dynamo=False,
        )
    except TypeError:
        # Older torch that doesn't accept `dynamo` kwarg
        torch.onnx.export(
            model, dummy,
            output_path,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
            opset_version=14,
        )
    logger.info("ONNX model saved to %s", output_path)
    return best_auc


def _spec_augment(x: "torch.Tensor", freq_mask: int = 4, time_mask: int = 8) -> "torch.Tensor":
    """Simple SpecAugment: mask random frequency bands and time steps."""
    import torch
    B, C, F, T = x.shape
    x = x.clone()
    for b in range(B):
        # Frequency masking
        f0 = torch.randint(0, max(1, F - freq_mask), (1,)).item()
        x[b, :, f0:f0 + freq_mask, :] = 0
        # Time masking
        t0 = torch.randint(0, max(1, T - time_mask), (1,)).item()
        x[b, :, :, t0:t0 + time_mask] = 0
    return x


def main():
    parser = argparse.ArgumentParser(description="Train SurakshaEdge audio CNN")
    parser.add_argument("--data-dir", default="data/audio", help="Directory with scream/ and negative/ subdirs")
    parser.add_argument("--output", default="models/audio_cnn.onnx")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()
    train(data_dir=args.data_dir, output_path=args.output, epochs=args.epochs,
          batch_size=args.batch_size, lr=args.lr)


if __name__ == "__main__":
    main()
