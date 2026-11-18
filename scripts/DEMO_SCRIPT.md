# SurakshaEdge — 5-Minute Demo Recording Script
**Team SingleThread | GNIOT, Greater Noida | SEVA FIRST 2026 | REG-008-OP-024**

---

## ✅ Pre-Recording Checklist (Complete Before Starting OBS)

```
[ ] Terminal 1 open in C:\SurakshaEdge\surakshaedge\
[ ] API server started: .\scripts\start_api.ps1 (or use https://surakshaedge.onrender.com)
[ ] Browser open at http://127.0.0.1:8000
[ ] Dashboard visible: map centered on GNIOT Knowledge Park II, 3 camera markers
[ ] Screen recorder active (OBS/Loom, 1920×1080)
[ ] Microphone checked & notifications silenced
[ ] Dashboard sound unmuted (click 🔊 Sound once to unlock AudioContext)
[ ] Existing alerts cleared (click 🔄 Clear All)
```

---

## 🎬 Demo Timeline (Target: 4:52)

### [0:00 – 0:35] THE HOOK — Shambhu narrates

> **Visual:** Live dashboard with GNIOT campus map, 3 camera markers

**Say:**
> "On August 4th, 2026, a teenage girl was assaulted on a moving bus traveling 47 kilometres from Pari Chowk to Delhi. The bus crossed police posts and dozens of CCTV cameras. Those cameras recorded everything — and warned nobody. We built SurakshaEdge to transform passive surveillance into an active, zero-touch guardian."

**Action:** Hover over each camera marker (`gate-1`, `gate-2`, `gate-3`) showing real GNIOT campus zones.

---

### [0:35 – 1:30] ARCHITECTURE & LIVE EDGE CCTV INSPECTOR — Shambhu narrates

> **Visual:** Click **● Live CCTV** button (or click the Gate-1 Camera Card)

**Say:**
> "SurakshaEdge processes video and audio locally in parallel. The vision branch runs YOLOv8n-Pose tracking 17 skeletal keypoints at 18 frames per second. It computes wrist velocity V_w, angular acceleration A_j, and proximity Q_p. The audio branch runs an MFCC-CNN detecting vocal distress S_t. Our core innovation is the 1.5-Second Temporal Fusion Gate: an alert triggers only when physical struggle kinematics AND acoustic distress coincide."

**Action:**
1. Click **● Live CCTV** (or click `gate-1` card) to open the Live Edge CCTV & Skeleton Inspector.
2. Point to the real-time COCO-17 skeleton lines, wrist velocity vector, and the live 40-band audio Mel-spectrogram.
3. Click **🏃 Hard Negative (Jogging)** — point out that $K_t$ rises from running, but $S_t$ remains ambient, so the gate locks and eliminates false alarms!
4. Click **✕** to close the camera modal.

---

### [1:30 – 2:30] LIVE ASSAULT ALERT & ENCRYPTED EVIDENCE REPLAY — Vaibhav operates, Shambhu narrates

> **Visual:** Dashboard main view → Click **🚨 Simulate ALERT**

**Say:**
> "Now let's observe an active assault sequence: grappling kinematics and scream distress arriving simultaneously within the 1.5-second gate."

**Action:**
1. Click **🚨 Simulate ALERT**:
   - Live Gauges spike: $K_t = 0.78$, $S_t = 0.85$.
   - Gate status flashes red: **⚡ ALERT**.
   - Map flies smoothly to GNIOT Gate-1 with pulsing red alert pin.
   - Emergency siren sounds and screen border strobes red.
   - Red ALERT incident card appears in the feed.
2. Click the new incident card in the Alert Feed to open the **Alert Detail Drawer**.
3. **Point to the 5s RAM Buffer Incident Replay**:
   - Show the looping 5-second struggle replay canvas with red crosshairs.
   - Point to badge: `🔒 AES-256-GCM ENCRYPTED | ZERO-PERSISTENCE RAM FLUSH`.
   - Explain: *"Notice no raw video is ever stored on disk. Frames circulate in a 5-second volatile RAM ring buffer. Only upon verified alert is an encrypted evidence packet generated."*
4. Click **✕** to close the detail panel.

---

### [2:30 – 3:30] MULTI-CAMERA DRILL & LIVE EXPORT — Vaibhav operates

> **Visual:** Click **▶ Run Demo Sequence**

**Say:**
> "Each camera node operates as an autonomous edge sentinel. Watch our multi-camera drill across the GNIOT campus."

**Action:**
1. Click **▶ Run Demo Sequence** — watch sequence progress:
   - Step 1: ADVISORY on Gate-2 (North Entrance)
   - Step 2: ADVISORY on Gate-1 (Main Gate)
   - Step 3: Critical ALERT on Gate-3 (Hostel Exit)
2. Show Gate-3 flashing red on the map.
3. Click the **⬇ Export** button in the Alert Feed header — show the instant JSON telemetry download (`suraksha_events.json`).

---

### [3:30 – 4:15] HARDWARE CAD & BLUEPRINT (Point 3 & 5) — Shambhu narrates

> **Visual:** Click **📐 Hardware CAD** in top navbar

**Say:**
> "SurakshaEdge operates as an inline edge appliance retrofitting existing RTSP IP cameras. Here is our 3D hardware blueprint."

**Action:**
1. Click **📐 Hardware CAD** — the 3D rotating blueprint opens.
2. Drag with the mouse to rotate the IP66 die-cast aluminum enclosure in 3D.
3. Click callout **1 (MEMS Horn)** → highlight acoustic horn with Gore-Tex waterproof membrane.
4. Click callout **2 (N100 SBC)** → highlight edge processor.
5. Click callout **5 (Heatsink)** → highlight passive convection fins.
6. Point to the BOM summary: *"Prototype benchtop unit costs ₹ 11,900; scalable to under ₹ 4,200 in batch production, or ₹ 0 additional hardware using existing campus NVR servers."*
7. Click **✕** to close.

---

### [4:15 – 4:52] BENCHMARK RIGOUR & CONCLUSION (Point 4) — Shambhu narrates

> **Visual:** Click **📊 Benchmarks** in top navbar

**Say:**
> "Every number we claim is directly measured from our 48 passing automated test suites:
> - Measured trigger-to-dashboard latency is 89.4 milliseconds — over 80% below our 450 ms ceiling.
> - Steady-state cloud uplink is 0 kbps — saving 99.98% bandwidth over continuous cloud streaming.
> - Steady power draw of 10.8 Watts yields 24.5 hours of continuous battery runtime during campus blackouts.
> 
> SurakshaEdge proves that we do not need to replace India's millions of CCTV cameras. We simply need to make them intelligent, vigilant, and privacy-respecting.
> Thank you."

**Action:**
1. Click **📊 Benchmarks** — show the Latency Budget table and 48/48 suites passed badge.
2. Click **📶 99.98% Bandwidth Reduction** tab.
3. End recording right at **04:50**.

---
*SurakshaEdge | Team SingleThread | GNIOT, Greater Noida | SEVA FIRST 2026 | REG-008-OP-024*
