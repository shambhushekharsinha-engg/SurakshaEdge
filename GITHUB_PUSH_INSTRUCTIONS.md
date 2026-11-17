# SurakshaEdge — GitHub & Render Deployment Guide

## ✅ GitHub — ALREADY DONE
**Repo URL:** https://github.com/shambhushekharsinha-engg/SurakshaEdge  
**Visibility:** Public  
**Branch:** `main` (2 commits)

---

## ☁️ Render Deployment (Free Forever — No Credit Card)

### Why Render (not Railway)?
| Feature | Render Free | Railway Free |
|---|---|---|
| Duration | **Forever** | 30-day trial only |
| Credit card | Not required | Required |
| Sleep after inactivity | 15 min (wakes in ~30s) | No |
| Region | Singapore (closest to India) | Auto |

---

### Step 1 — Deploy on Render

**Option A — One-Click Deploy Button (Easiest):**

Click: https://render.com/deploy?repo=https://github.com/shambhushekharsinha-engg/SurakshaEdge

1. Sign in with GitHub (use `shambhushekharsinha-engg`)
2. Render reads `render.yaml` automatically
3. Click **Apply** — build takes ~3-5 minutes

**Option B — Manual Setup:**

1. Go to https://dashboard.render.com → **New** → **Web Service**
2. Connect GitHub → select `shambhushekharsinha-engg/SurakshaEdge`
3. Fill in:
   - **Name:** `surakshaedge`
   - **Region:** Singapore
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
4. Add Environment Variables:
   | Key | Value |
   |---|---|
   | `SURAKSHA_API_TOKEN` | `demo-token` |
   | `SURAKSHA_CONFIG` | `configs/demo.yaml` |
   | `SURAKSHA_PRODUCTION` | `false` |
   | `SURAKSHA_KEY` | *(click "Generate" in Render)* |
5. Click **Create Web Service**

---

### Step 2 — Verify Deployment

After ~3-5 minutes, your live URL will be:
`https://surakshaedge.onrender.com` (or `https://surakshaedge-XXXX.onrender.com`)

Test these URLs:
- `https://YOUR_RENDER_URL/health` → `{"status":"ok","audio_mode":"energy_fallback",...}`
- `https://YOUR_RENDER_URL/` → Dashboard loads with GNIOT campus map
- Click **🚨 Simulate ALERT** → Red pin appears on map

> Note: `audio_mode` will show `energy_fallback` on Render (no mic hardware in cloud).  
> Say in pitch: "Cloud API instance; local edge node uses MFCC-CNN ACTIVE mode."

---

### Step 3 — Get Your Live Demo URL for Screen 2 Submission

Paste in Screen 2 Portal → Point 2 (Live Demo URL):
```
GitHub: https://github.com/shambhushekharsinha-engg/SurakshaEdge
Live Demo: https://surakshaedge.onrender.com
```

---

## Future Updates — Push Changes

```powershell
cd C:\SurakshaEdge\surakshaedge
git add -A
git commit -m "your message"
git push origin main
```
Render auto-deploys on every push to `main`.

---
*SurakshaEdge | Team SingleThread | GNIOT, Greater Noida | SEVA FIRST 2026 | REG-008-OP-024*
