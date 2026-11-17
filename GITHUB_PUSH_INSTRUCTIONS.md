# SurakshaEdge — GitHub Publishing & Railway Deployment Guide

## Step 1: Create GitHub Repository

1. Go to: **https://github.com/new**
2. Fill in:
   - **Repository name:** `SurakshaEdge`
   - **Description:** `Edge AI safety sentinel — SEVA FIRST 2026 | REG-008-OP-024 | GNIOT`
   - **Visibility:** Public
   - ⚠️ **DO NOT** check "Add a README" or "Add .gitignore" (we have both)
3. Click **Create repository**

## Step 2: Push Code to GitHub

Run these commands in PowerShell from `C:\SurakshaEdge\surakshaedge\`:

```powershell
cd C:\SurakshaEdge\surakshaedge

# Add GitHub as the remote origin (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/SurakshaEdge.git

# Set main branch and push
git branch -M main
git push -u origin main
```

> **If asked for credentials:** Use your GitHub username and a [Personal Access Token](https://github.com/settings/tokens) (classic, with `repo` scope) as the password.

## Step 3: Deploy on Railway (Free Tier)

1. Go to: **https://railway.app** → Sign in with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select the `SurakshaEdge` repository
4. Railway auto-detects `Procfile` and starts the build
5. Set the following **Environment Variables** in Railway Settings:

| Variable | Value | Note |
|---|---|---|
| `SURAKSHA_API_TOKEN` | `demo-token` | Bearer token for API |
| `SURAKSHA_KEY` | *(generated below)* | AES-256 encryption key |
| `SURAKSHA_CONFIG` | `configs/demo.yaml` | Config file path |
| `SURAKSHA_PRODUCTION` | `false` | Keeps /simulate endpoint enabled |

**Generate SURAKSHA_KEY** (run this locally, copy the output):
```powershell
python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
```

6. Click **Deploy** — Railway builds and starts the app in ~2-3 minutes
7. Click the generated Railway URL (e.g., `https://surakshaedge-production.up.railway.app`)
8. The dashboard will load with the GNIOT campus map!

## Step 4: Share the Live Demo URL

After deployment:
- **Dashboard URL:** `https://your-app-name.up.railway.app`
- Share this URL in the SEVA FIRST Screen 2 submission form as the **Live Demo Link**
- The dashboard shows the Leaflet map, Sim ALERT/ADVISORY buttons, real-time WebSocket updates

## Note on the Edge Pipeline

The deployed Railway instance runs only the **API + Dashboard** (no webcam/camera needed).
The **edge ML pipeline** (YOLOv8 + MFCC-CNN) runs locally on your laptop and POSTs events to the API.

For the submission video:
1. Start the API locally: `.\scripts\start_api.ps1`
2. Open `http://127.0.0.1:8000` for the demo (or the Railway URL)
3. Run: `python scripts/demo_injector.py --url http://127.0.0.1:8000 --token demo-token`
4. Record with OBS Studio / Loom / Camtasia

---
*SurakshaEdge | Team SingleThread | GNIOT, Knowledge Park II, Greater Noida | SEVA FIRST 2026*
