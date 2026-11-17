# SurakshaEdge 🛡

> **Edge AI Safety Sentinel** — Dual-stream physical assault + vocal distress detection from CCTV  
> **Team SingleThread** · GNIOT, Knowledge Park II, Greater Noida · **SEVA FIRST 2026** · REG-008-OP-024

[![Tests](https://img.shields.io/badge/tests-48%20passed-brightgreen)](https://github.com/SingleThread-GNIOT/SurakshaEdge)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-AGPL--3.0-orange)](LICENSE)
[![MFCC-CNN Active](https://img.shields.io/badge/audio-MFCC--CNN_active-green)](models/)
[![Latency](https://img.shields.io/badge/latency-54.8ms_p50_CPU-blue)](eval/)
[![FPS](https://img.shields.io/badge/throughput-18_FPS_CPU-blue)](eval/)

> **Live Dashboard** — Start the API and open `http://127.0.0.1:8000` to see the GNIOT campus map with real-time alerts.

---

## 🚀 Quick Start (3 Commands)

```powershell
cd C:\SurakshaEdge
pip install -e surakshaedge --no-deps
cd surakshaedge && .\scripts\start_api.ps1
```

Then open **http://127.0.0.1:8000** — click **🚨 Simulate ALERT** to see the full pipeline demo.

---

## ☁️ Deploy on Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

1. Push repo to GitHub (see [GITHUB_PUSH_INSTRUCTIONS.md](GITHUB_PUSH_INSTRUCTIONS.md))
2. Connect Railway → "Deploy from GitHub" → select `SurakshaEdge`
3. Set env vars: `SURAKSHA_API_TOKEN=demo-token`, `SURAKSHA_KEY=<generated>`, `SURAKSHA_CONFIG=configs/demo.yaml`

---

## What It Does

SurakshaEdge monitors CCTV feeds in real time. It detects physical assault by combining:

- **YOLOv8n-Pose** → kinematic distress score K_t (wrist speed + limb angle + close contact)
- **MFCC-CNN** → scream probability S_t (audio branch)
- **FusionGate** → ALERT when both exceed thresholds within 1.5 s; ADVISORY on either alone

On ALERT: AES-256-GCM encrypted clip is stored, GPS pin appears on the Leaflet dashboard, siren plays, WebSocket pushes to all clients. No face recognition, no persistent video.

---

## Quick Start

### 1. Prerequisites

```powershell
# Python 3.10+ required (tested on 3.13.3)
cd C:\SurakshaEdge
pip install -e surakshaedge --no-deps     # installs as editable package
pip install lap>=0.5.12                   # ByteTrack dependency
# YOLOv8 weights (auto-downloaded on first run, or manually):
python -c "from ultralytics import YOLO; YOLO('yolov8n-pose.pt')"
Move-Item yolov8n-pose.pt surakshaedge\models\
```

### 2. Run Tests

```powershell
cd C:\SurakshaEdge\surakshaedge
python -m pytest tests/unit tests/integration tests/privacy -v -W default
# Expected: 35+ passed, 0 warnings
```

### 3. Run Benchmark

```powershell
python eval/benchmark.py --frames 1000 --device cpu
# Expected: pose p50~67ms, ~14 FPS on CPU at imgsz=640
#           Use configs/cpu.yaml (imgsz=320) for ~30 FPS
```

### 4. Test Pipeline on a Clip

```powershell
# Synthetic clip (no people — K_t stays 0, that's correct):
python -m surakshaedge.edge.pipeline --config configs/cpu.yaml --source data\clips\synthetic_short.mp4

# Real clip (place at data\clips\test1.mp4 first):
python -m surakshaedge.edge.pipeline --config configs/cpu.yaml --source data\clips\test1.mp4
```

### 5. Start API + Dashboard

**Terminal 1 — API server:**
```powershell
cd C:\SurakshaEdge\surakshaedge
$env:SURAKSHA_KEY = python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
$env:SURAKSHA_API_TOKEN = "demo-token"
python -m uvicorn surakshaedge.api.main:app --host 127.0.0.1 --port 8000
```

**Browser:** `http://127.0.0.1:8000`  
Click **🧪 Sim ALERT** to test — confirm red map pin, feed entry, siren, strobe, score breakdown.

**Terminal 2 — Pipeline feeding the API (Gate G1):**
```powershell
cd C:\SurakshaEdge\surakshaedge
$env:SURAKSHA_API_TOKEN = "demo-token"
python -m surakshaedge.edge.pipeline --config configs/cpu.yaml --source data\clips\test1.mp4
```
When ALERT appears on the dashboard map: Gate G1 is met.

---

## Architecture

```
CCTV / file
    │
    ▼ VideoIngest (OpenCV, throttled replay)
    │
    ├─► PoseEstimator (YOLOv8n-Pose + ByteTrack)
    │       │
    │       ▼ tracks: [Track(id, keypoints 17×3, bbox)]
    │
    ├─► KinematicsEngine
    │       K_t = 0.4·V_w + 0.3·A_j + 0.3·Q_p
    │       flag = K_t ≥ 0.62 for ≥ 0.4 s
    │
    ├─► AudioScorer (MFCC-CNN or energy fallback)
    │       S_t ∈ [0,1]  flag = S_t ≥ 0.70 for ≥ 0.5 s
    │
    ▼ FusionGate
        ALERT:    K_flag ∧ S_flag within 1.5 s window
        ADVISORY: K_t ≥ 0.75 sustained 1.0 s  OR  S_t ≥ 0.85 sustained 0.5 s
        Cooldown: 10 s per zone (escalation on +0.15 score rise)
    │
    ▼ PrivacyManager → AES-256-GCM clip
    │
    ▼ POST /events → FastAPI → WebSocket → Leaflet dashboard
```

---

## Configuration

| File | Purpose |
|---|---|
| `configs/demo.yaml` | Full-res (imgsz=640), live camera |
| `configs/cpu.yaml`  | Reduced-res (imgsz=320), faster on CPU, for replay/demo |

Key env vars:
| Variable | Purpose | Example |
|---|---|---|
| `SURAKSHA_KEY` | AES-256 key (base64 32 bytes) | `python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"` |
| `SURAKSHA_API_TOKEN` | Bearer token for API | `demo-token` |
| `SURAKSHA_CONFIG` | Config path for API lifespan | `configs/demo.yaml` |
| `SURAKSHA_PRODUCTION` | Set `true` to disable /simulate | `false` |

---

## Data Collection (Vaibhav)

### Video Clips

Place in `data/clips/`, name format: `CLASS_SESSION_SCENE_TAKE.mp4`

| Prefix | Class | Example |
|---|---|---|
| `POS_` | positive (struggle + scream) | `POS_S01_gate_T01.mp4` |
| `VIS_` | vision-only (struggle, quiet) | `VIS_S01_corridor_T01.mp4` |
| `AUD_` | audio-only (scream offscreen) | `AUD_S01_gate_T01.mp4` |
| `NEG_` | hard negative (sports, dance…) | `NEG_S01_sports_T01.mp4` |

Fill `eval/labels.csv` for each clip with: `clip_id, class, onset_s, end_s, expected_tier, performers, location, lighting, split, consent_form_id, date`

Splits: `dev` (tune thresholds), `validation` (monitor training), `test` (lock 2 Nov, run once).

### Audio Files

- `data/audio/scream/*.wav` — 30-40 scream / vocal distress clips, 16 kHz, ≥1 s each
- `data/audio/negative/*.wav` — 30-40 non-screams (talking, clapping, laughing, crowd)

### Train Audio CNN

```powershell
pip install torch scikit-learn   # if not already installed
python training/audio_cnn/train.py --data-dir data/audio --output models/audio_cnn.onnx --epochs 30
# Target: val AUC > 0.9
# Then update configs/cpu.yaml: audio.model: models/audio_cnn.onnx
```

---

## Evaluation

```powershell
# Dev split (tune on these):
python eval/run_eval.py --split dev --config configs/cpu.yaml

# Validation split (monitor training):
python eval/run_eval.py --split validation --config configs/cpu.yaml

# Test split (run ONCE on 2 Nov, never before):
python eval/run_eval.py --split test --config configs/cpu.yaml
```

Targets: Recall ≥ 85%, FAR < 5%, latency to alert < 450 ms (< 3 s for event-level).

---

## Gates

| Gate | Deadline | Criterion |
|---|---|---|
| **G1** | Tue 27 Oct 8pm | Real recorded clip → ALERT on dashboard map (MISSED — record asap) |
| **G2** | Sun 2 Nov 8pm | 75% recall on dev clips (≥ 10 positives) |
| **G3** | Tue 4 Nov 8pm | CNN trained, dashboard shows `mfcc_cnn` mode |
| **G4** | Sat 7 Nov 8pm | Recall ≥ 85%, FAR < 5%, latency < 450 ms (measured) |
| **Demo** | Tue 10 Nov | End-to-end on jury's camera feed |

---

## Privacy

- **No face recognition, no persistent video**
- Frames kept in RAM ring buffer (5 s); at ALERT, 5-s clip encrypted with AES-256-GCM and stored in SQLite only
- Audit log at `results/audit.jsonl` — contains only metadata, no media bytes
- `PT-01` privacy test: 10 s soak confirms no media files written during normal operation

Full 10-minute PT-01: `$env:SURAKSHA_PRIVACY_SOAK=600; python -m pytest tests/privacy::test_pt01_no_media_files_written_sustained -v -s`

---

## Audio Honesty

Until `models/audio_cnn.onnx` is trained, the pipeline runs in **energy fallback** mode.  
Dashboard shows `⚠ AUDIO: ENERGY FALLBACK` banner.  
**Do not describe this as the MFCC-CNN scream detector to the jury.**

---

## Team

| Person | Role |
|---|---|
| Shambhu Shekhar Sinha | Software, ML, API, Dashboard |
| Vaibhav Kumar Tiwari | Data collection, consent, recording |

License: **AGPL-3.0**
