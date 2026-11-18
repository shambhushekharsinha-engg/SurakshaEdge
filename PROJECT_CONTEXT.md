# SurakshaEdge — Project Context (GSD)
**Team SingleThread · GNIOT, Knowledge Park II · SEVA FIRST 2026 · REG-008-OP-024**
**Demo: Tuesday 10 November 2026**
*Last updated: 2026-11-01 D12*

## Architecture (LOCKED)

```
Camera → VideoIngest → PoseEstimator (YOLOv8n-pose) → KinematicsEngine → K_t, K_flag
Microphone → AudioScorer (MFCC-CNN / Energy Fallback) → S_t, S_flag
                                                        ↓
                                             FusionGate (1.5s window)
                                                        ↓
                                      ALERT / ADVISORY / NONE
                                                        ↓
                                      FastAPI → WebSocket → Dashboard
```

### Scoring
- K_t = 0.4·V_w + 0.3·A_j + 0.3·Q_p
- K_flag: K_t ≥ 0.62 for ≥ 0.4s
- S_flag: S_t ≥ 0.70 for ≥ 0.5s
- ALERT: K_flag AND S_flag within 1.5s
- ADVISORY: K_t ≥ 0.75 for 1.0s OR S_t ≥ 0.85 for 0.5s
- Cooldown: 10s. Escalation: +0.15 score rise during cooldown.

### Privacy
- RAM ring buffer 5s only — no persistent video
- AES-256-GCM encrypted clip on ALERT only
- SQLite event store (scores, timestamps, no biometrics)
- No face recognition, no re-ID

## Package Structure

```
C:\SurakshaEdge\               ← install root (pip install -e surakshaedge --no-deps)
C:\SurakshaEdge\surakshaedge\  ← project root AND Python package
  edge/          pipeline, pose, audio, kinematics, fusion, ingest, privacy
  api/           FastAPI app, schemas, security, store
  dashboard/     index.html (single-file dashboard)
  training/      audio_cnn/train.py
  eval/          benchmark.py, run_eval.py, labels.csv
  scripts/       gen_synthetic_audio.py, demo_injector.py, run_demo.ps1
  configs/       cpu.yaml, demo.yaml
  models/        yolov8n-pose.pt, audio_cnn.onnx (when trained)
  data/          clips/, audio/scream/, audio/negative/
  tests/         unit/, integration/, privacy/
```

## Key Commands

```powershell
# Run tests
cd C:\SurakshaEdge\surakshaedge
python -m pytest tests/unit tests/integration tests/privacy -q --tb=short

# Start API (in your own terminal)
$env:SURAKSHA_KEY = python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
$env:SURAKSHA_API_TOKEN = "demo-token"
python -m uvicorn surakshaedge.api.main:app --host 127.0.0.1 --port 8000

# Run pipeline on clip
python -m surakshaedge.edge.pipeline --config configs/cpu.yaml --source data\clips\synthetic_short.mp4

# Train audio CNN
python training/audio_cnn/train.py --data-dir data/audio --output models/audio_cnn.onnx --epochs 30

# Demo injector (posts synthetic events to running API)
python scripts/demo_injector.py --url http://127.0.0.1:8000 --token demo-token

# Benchmark
python eval/benchmark.py --frames 1000 --device cpu
```

## Install

```powershell
# From C:\SurakshaEdge\ (parent of surakshaedge\)
pip install -e surakshaedge --no-deps
```

## Constraints (NON-NEGOTIABLE)

1. NEVER present energy fallback as MFCC-CNN
2. G1 = real clip producing ALERT on map (not a test)
3. Module paths: surakshaedge.api.main:app, surakshaedge.edge.pipeline
4. Editable install from parent dir
5. pyproject.toml: build-backend=setuptools.build_meta, license="AGPL-3.0"
6. Full PT-01 (10 min, SURAKSHA_PRIVACY_SOAK=600) before demo

## Gates

| Gate | Criterion | Status |
|------|-----------|--------|
| G1 | Real clip → ALERT on map | NOT MET (synthetic CNN trained) |
| G2 | Audio CNN val AUC ≥ 0.9 on real data | CNN trained on synthetic |
| G3 | Dev split eval, recall ≥ 70% | Blocked on real clips |
| G4 | Test split, ≥85% recall / <5% FAR | Blocked |

## Test Count: 38+ passing

## Installed packages
Python 3.13.3, ultralytics, lap>=0.5.13, torch 2.13.0+cpu, sklearn,
onnx, onnxruntime, sounddevice, soundfile, scipy, fastapi, uvicorn,
cryptography, pyyaml, requests, pytest

## Dashboard Features (v2 — D12)
- Mobile-first responsive (mobile tabs / desktop sidebar)
- Leaflet map with zone polygons (GNIOT campus boundary)
- Camera markers with status colors
- Alert markers: one per camera, auto-expire 15s
- Help modal (operator guide)
- Settings panel (volume, auto-clear, tile type, strobe toggle)
- Keyboard shortcuts: M/H/C/Esc/S
- Siren: AudioContext unlocked on first user gesture
- Strobe: 3-flash CSS animation, auto-cleanup
- Audio mode badge (ENERGY FALLBACK / MFCC-CNN ACTIVE)
- Zone info overlay
- Clear map / Show cameras buttons
- Export events as JSON
- Sim ALERT and Sim ADVISORY buttons
