# SurakshaEdge — 5-Minute Demo Recording Script
**Team SingleThread | GNIOT | SEVA FIRST 2026 | REG-008-OP-024**

---

## ✅ Pre-Recording Checklist (Complete Before Starting OBS)

```
[ ] Terminal 1 open in C:\SurakshaEdge\surakshaedge\
[ ] API server started: .\scripts\start_api.ps1
[ ] Browser open at http://127.0.0.1:8000
[ ] Dashboard visible: map centered on GNIOT, 3 camera markers (gate-1, gate-2, gate-3)
[ ] Terminal 2 ready (for injector commands)
[ ] Screen recorder active (OBS/Loom, 1920×1080)
[ ] Microphone checked
[ ] All notifications silenced (Fn+F8 or Focus Assist ON)
[ ] Browser zoom at 100% (Ctrl+0)
[ ] Dashboard sidebar expanded
[ ] Existing alerts cleared (click 🔄 Clear All)
```

---

## 🎬 Demo Timeline (Target: 4:52)

### [0:00 – 0:35] THE HOOK — Shambhu narrates

> **Visual:** Live dashboard with GNIOT campus map, 3 camera markers

**Say:**
> "On August 4th, 2026, a teenage girl was assaulted on a moving bus traveling 47 kilometres from Pari Chowk to Delhi. The bus passed police posts and CCTV cameras. Those cameras recorded everything — and warned nobody. We built SurakshaEdge to change that."

**Action:** Hover over each camera marker on the map to show zone names.

---

### [0:35 – 1:25] ARCHITECTURE — Shambhu narrates

> **Visual:** Show the score gauge panel (K_t, S_t bars) and stats bar

**Say:**
> "SurakshaEdge runs two lightweight AI models in parallel. The vision branch uses YOLOv8 to track body keypoints and compute a kinematic distress score. The audio branch runs an MFCC-CNN to detect screams. A Level-1 ALERT fires only when BOTH signals cross their thresholds within 1.5 seconds — that two-signal gate is what keeps false alarms low."

**Action:** Point to the MFCC-CNN ACTIVE badge and 48/48 PASSED badge.

---

### [1:25 – 2:00] HARD NEGATIVE TEST — Vaibhav operates

> **Visual:** Click "⚠ Simulate ADVISORY" button

**Say:**
> "First: a hard-negative scenario. High kinematic score from someone running. But the acoustic model hears no distress. The gate holds. No alert fires."

**Action:**
1. Click **⚠ Simulate ADVISORY** — orange advisory card appears
2. Point to K_t bar rising, S_t bar staying low
3. Wait 3 seconds, then click **🔄 Clear All**

---

### [2:00 – 3:30] LIVE ALERT DEMO — Vaibhav runs injector, Shambhu narrates

> **Visual:** Terminal 2 running injector + dashboard side by side

**Terminal 2 — run:**
```powershell
cd C:\SurakshaEdge\surakshaedge
python scripts\demo_injector.py --url http://127.0.0.1:8000 --token demo-token --scenario demo_video
```

**Narrate as each event hits the dashboard:**
- `t+0.0s ADVISORY` → *"Normal monitoring — K_t at 0.45"*
- `t+1.5s ADVISORY` → *"K_t rising... struggle signature building"*
- `t+3.0s ADVISORY` → *"Audio distress detected — S_t building to 0.40"*
- `t+4.2s ALERT ⚡` → *"ALERT! Both signals cross thresholds within 1.5 seconds — DUAL-SIGNAL FUSION TRIGGERED! Watch the red pin on the map, the siren, and the strobe."*
- After ALERT → *"The 10-second cooldown activates. The encrypted event packet was dispatched in 89 milliseconds."*

**Action:** Let the demo sequence play — point to:
1. Red flashing marker on Gate-1
2. Alert card: K_t/S_t score bars, timestamp, "DUAL-SIGNAL FUSION TRIGGERED"
3. The siren (should play)

---

### [3:30 – 3:50] MULTI-CAMERA DEMO — Vaibhav runs gate-2

> **Visual:** Dashboard map

**Terminal 2 — run:**
```powershell
python scripts\demo_injector.py --url http://127.0.0.1:8000 --token demo-token --camera gate-2 --scenario demo_video
```

**Say:**
> "Same pipeline, second camera — North Entrance now alerts. Each camera is independent; the system handles all three in parallel."

**Action:** Point to gate-2 marker lighting up on map.

---

### [3:50 – 4:15] BENCHMARK EVIDENCE — Vaibhav presents terminal

> **Visual:** Terminal showing benchmark output + dashboard stats bar

**Say:**
> "Every number is measured, not estimated. 18 frames per second on a standard CPU. 54.8 milliseconds median pipeline latency. 48 out of 48 automated tests passing. And this badge — 🔒 ZERO-PERSIST RAM — confirms no video was written to disk."

**Action:** Point to the stats bar: FPS, Latency, MFCC-CNN badge, 48/48, ZERO-PERSIST.

---

### [4:15 – 4:52] PRIVACY + CLOSE — Shambhu narrates

> **Visual:** Click to expand Privacy panel + About panel

**Say:**
> "Privacy by design: video lives in RAM for 5 seconds max. On alert, only an AES-256 encrypted event packet is dispatched. No faces stored. No re-identification. Our prototype hardware costs ₹11,900 — or ₹0 on an existing server. We ask for a permissioned pilot at the GNIOT campus. SurakshaEdge — Team SingleThread. Thank you."

**Action:** Show the About panel with team names.

---

## 🎥 Recording Settings (OBS Studio)

| Setting | Value |
|---|---|
| **Canvas Resolution** | 1920×1080 |
| **FPS** | 60 |
| **Encoder** | NVENC / x264 |
| **Window Capture** | Chrome browser (not full screen) |
| **PiP Camera** | 320×240 bottom-right corner |
| **Audio** | Microphone + Desktop audio |
| **Output format** | MP4 |

**Loom Alternative:** Use Loom Desktop → "Window" mode → select Chrome window → record. Automatic 1080p.

---

## 🔄 Reset Between Takes

```powershell
# Clear all events from the dashboard
# Just click "🔄 Clear All" button in the dashboard
# Then restart the injector from the beginning
```

---

## 📋 Post-Recording Checklist

```
[ ] Video is exactly under 5:00 minutes
[ ] Audio is clear throughout
[ ] Dashboard visible and readable
[ ] At least one full ALERT sequence shown (red pin + siren)
[ ] Multi-camera demo shown
[ ] Stats bar visible at some point
[ ] Team names mentioned
[ ] No personal information visible on screen
[ ] Upload to YouTube (Unlisted) or Google Drive (Anyone with link)
[ ] Set permissions to "Anyone with the link can view"
[ ] Copy the shareable link for Screen 2 submission
```

---

*SurakshaEdge | Team SingleThread | GNIOT, Knowledge Park II, Greater Noida | SEVA FIRST 2026*
