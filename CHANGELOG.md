# Changelog

All notable changes to SurakshaEdge are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [0.4.0] — 2026-11-18

### Added
- **Rate limiting middleware** — token-bucket (60 req/min, burst 10) on `/events`, `/simulate`
- **Structured JSON logging** — every request gets a UUID trace-ID; latency logged in ms
- **Security headers** — CSP, HSTS, X-Frame-Options DENY, X-Content-Type nosniff, Referrer-Policy
- **Prometheus metrics endpoint** — `GET /metrics/prometheus` exports `surakshaedge_*` counters
- **`/livez` + `/readyz`** liveness/readiness probes (Kubernetes-style)
- **GitHub Actions CI** — ruff lint + 48-test suite on every push/PR to `main`
- **Dockerfile** — multi-stage, non-root `appuser`, HEALTHCHECK, production-ready
- **PWA manifest + service worker** — installable as mobile app, offline splash
- **API status badge** in dashboard header — live poll of `/health` every 30 s
- **Input validation** — Pydantic validators for `tier` enum, GPS bounds, score 0–1 range

### Changed
- Dashboard header subtitle: removed `GNIOT ×` prefix from `SEVA FIRST 2026` phrase
- `.env.example` — fully documented with all env vars, descriptions, and example values
- `api/middleware.py` — consolidated all middleware in one module

---

## [0.3.0] — 2026-11-17

### Added
- **Live CCTV & Skeleton Inspector modal** — animated COCO-17 skeleton canvas with real-time telemetry
- **5-second RAM-buffer incident replay** — looping canvas replay in alert drawer, AES-256-GCM badge
- **3D Hardware CAD Blueprint modal** — WebGL-style die-cast enclosure with component callouts
- **Benchmark & Calculation Dossier** — 4-tab modal: latency budget, bandwidth, battery, false-positive
- **Audio voiceover** — 7-act MP3 narration (04:48 total) using `edge-tts` `en-IN-PrabhatNeural`
- `scripts/PITCH_TELEPROMPTER_SCRIPT.md` — audio-calibrated word-for-word teleprompter
- `scripts/DEMO_SCRIPT.md` — 7-act click-through demo guide

---

## [0.2.0] — 2026-11-16

### Fixed
- `ModuleNotFoundError: No module named 'surakshaedge'` on Render — fixed with `importlib.util` shim in `main.py`
- Mixed-content WebSocket block on HTTPS — `ws://` → dynamic `wss://`/`ws://` based on `location.protocol`
- Map watermark `API KEY REQUIRED` — replaced CartoDB tiles with Esri Dark Canvas (free, no key)
- Map coordinates corrected to real GNIOT campus: `28.4600, 77.4952` (Knowledge Park II)

### Added
- Esri Dark Canvas tile layer as proper no-key dark mode map
- OpenStreetMap Street tiles as clean default (no watermarks)
- `.python-version` file pinned to `3.11.9`

### Changed
- `render.yaml` — added `PYTHON_VERSION: 3.11.9` to avoid Python 3.14 experimental issues

---

## [0.1.0] — 2026-11-15

### Added
- FastAPI REST API with `/events`, `/health`, `/metrics`, `/cameras`, `/zones`, `/export/events`
- WebSocket `/ws/alerts` with 10-second heartbeat
- AES-256-GCM encrypted clip storage schema
- Bearer token authentication + replay-window protection
- SQLite event persistence with 24-hour retention + hourly purge
- YOLOv8n-pose skeleton tracking (`edge/pose.py`)
- MFCC-CNN audio scorer with energy fallback (`edge/audio.py`)
- Kinematics engine — velocity, acceleration, joint-angle, fusion score (`edge/kinematics.py`, `edge/fusion.py`)
- Privacy subsystem — zero disk persistence, RAM-only ring buffer, AES-256-GCM (`edge/privacy.py`)
- 48-test suite (unit + integration + privacy) — 100% passing
- Dashboard — Leaflet map, camera grid, alert drawer, metrics panel
- Demo injector with 4 scenarios (S1–S4), GPS-synced to GNIOT campus
- `render.yaml` for Render.com free-tier deployment
- `railway.toml` for Railway.app deployment

---

[0.4.0]: https://github.com/shambhushekharsinha-engg/SurakshaEdge/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/shambhushekharsinha-engg/SurakshaEdge/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/shambhushekharsinha-engg/SurakshaEdge/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/shambhushekharsinha-engg/SurakshaEdge/releases/tag/v0.1.0
