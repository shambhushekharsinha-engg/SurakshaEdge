# Runbook Corrections

The printed *SurakshaEdge Setup Guide and Runbook (v0.1, 20 Oct 2026)* uses bare module paths.
The correct paths after packaging are:

| Runbook says | Use this instead |
|---|---|
| `api.main:app` | `surakshaedge.api.main:app` |
| `edge.pipeline` | `surakshaedge.edge.pipeline` |
| `eval/run_eval.py` | `python eval/run_eval.py` (run from `surakshaedge/`) |
| `eval/benchmark.py` | `python eval/benchmark.py` (run from `surakshaedge/`) |

## Correct startup commands (copy-paste ready)

```powershell
# Activate venv first
.venv\Scripts\Activate.ps1

# Terminal 1 — API + dashboard (http://127.0.0.1:8000)
uvicorn surakshaedge.api.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — Edge pipeline (live webcam)
python -m surakshaedge.edge.pipeline --config configs/demo.yaml

# Terminal 2 alternative — Replay a labelled clip
python -m surakshaedge.edge.pipeline --config configs/demo.yaml --source data/clips/POS_S01_gate_T01.mp4

# CPU-only fallback (no GPU)
python -m surakshaedge.edge.pipeline --config configs/cpu.yaml

# Run all tests
pytest tests/unit/ tests/integration/ tests/privacy/ -v -W default

# Benchmark (CPU)
python eval/benchmark.py --frames 1000 --device cpu

# Evaluation (after clips are recorded)
python eval/run_eval.py --split dev --config configs/demo.yaml

# Full 10-minute privacy soak test (before demo day)
$env:SURAKSHA_PRIVACY_SOAK = "600"
pytest tests/privacy/test_privacy_system.py::test_pt01_no_media_files_written_sustained -v -s
```

## Audio mode warning

Until `models/audio_cnn.onnx` is trained and set in `configs/demo.yaml`:
- `audio.model` is `null` → pipeline uses **energy fallback**
- S_t detects ANY loud sound, not specifically screams
- Dashboard shows orange **⚠ AUDIO: ENERGY FALLBACK** banner
- Do NOT present S_t as a scream detector to the jury in this mode

To train:
```powershell
# After recording scream/ and negative/ WAVs into data/audio/
python training/audio_cnn/train.py --data-dir data/audio --output models/audio_cnn.onnx
# Then set in configs/demo.yaml:  audio.model: models/audio_cnn.onnx
```
