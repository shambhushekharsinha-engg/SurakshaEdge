# SurakshaEdge — Field Trial Validation Protocol
**Version:** 1.0 | **Stage:** IV (Field Deployment) → V (Viva Defense)
**Document Owner:** Student Lead — Shambhu Kumar Shekhar Sinha
**Last Updated:** 2026-11-22
**Classification:** Internal / Evaluation Use Only

---

## 1. Executive Summary

### 1.1 Purpose
This Field Trial Validation Protocol (FTVP) governs the controlled, 72-hour deployment and systematic evaluation of the **SurakshaEdge** real-time assault-detection system on the GNIOT campus. It defines the hardware configuration, observation methodology, performance acceptance criteria, compliance checklist, and sign-off requirements necessary for Stage-IV completion and Stage-V jury defense.

### 1.2 Scope
| Item | Detail |
|---|---|
| System Under Test | SurakshaEdge v0.4.1 — Edge AI assault detection pipeline |
| Deployment Environment | GNIOT Campus, Greater Noida, Uttar Pradesh |
| Trial Duration | 72 continuous hours (3 × 24-hour observation slots) |
| Node Count | 5 edge nodes |
| Sensor Modalities | Audio (Knowles MEMS), Vision (IR camera), Pose estimation |
| Regulatory Framework | DPDP Act 2023, IT Act 2000, GNIOT Ethics Board approval |
| Operator Count | 2 trained security-guard operators (rotating shifts) |

### 1.3 Success Gate
The field trial is considered **PASSED** if all five performance targets in Section 5 are met across **at least 48 of the 72 hours** of continuous observation, with no critical safety incidents or data-privacy breaches.

---

## 2. Deployment Map — 5-Node GNIOT Campus Layout

```
              [GNIOT CAMPUS BOUNDARY]
     ┌──────────────────────────────────────┐
     │                                      │
 N1  │  ◉ Gate-1 (Main Entrance)            │  ← Primary chokepoint
     │    Lat: 28.4720, Lon: 77.5035        │
     │                                      │
 N2  │  ◉ Hostel Road                       │  ← High-footfall corridor
     │    Lat: 28.4716, Lon: 77.5041        │
     │                                      │
 N3  │  ◉ Central Library                   │  ← Mixed gender zone
     │    Lat: 28.4722, Lon: 77.5038        │
     │                                      │
 N4  │  ◉ Perimeter East                    │  ← Blind-spot coverage
     │    Lat: 28.4718, Lon: 77.5048        │
     │                                      │
 N5  │  ◉ Transit Corridor                  │  ← Egress monitoring
     │    Lat: 28.4714, Lon: 77.5033        │
     └──────────────────────────────────────┘
              [Control Room: Security Office]
```

### 2.1 Node Summary Table

| Node ID | Location | Coverage Area (m²) | Expected Peak Footfall/hr | Lighting Condition |
|---|---|---|---|---|
| N1 | Gate-1 (Main Entrance) | ~120 | 400–600 | Well-lit + IR supplement |
| N2 | Hostel Road | ~200 | 150–300 | Mixed, IR critical at night |
| N3 | Central Library | ~180 | 80–200 | Indoor fluorescent |
| N4 | Perimeter East | ~350 | 20–60 | Dark, IR primary |
| N5 | Transit Corridor | ~150 | 200–350 | Fluorescent + exit signage |

### 2.2 Network Topology
- Each node connects via **campus LAN (Cat 6)** to the control-room server.
- WebSocket push endpoint: `ws://<control-room-IP>:8000/ws/alerts`
- Dashboard accessible at: `http://<control-room-IP>:8000/dashboard`
- Fallback: 4G dongle (Jio/Airtel) on Node N4 (perimeter, no cable run).

---

## 3. Hardware Checklist — Per Node

Each of the 5 nodes must be verified against the following checklist **before** powering on. Record the serial numbers in the Data Collection Sheet (Section 9).

### 3.1 Core Components

| # | Component | Specification | Qty | Pre-Deploy Check | Inspector Initials |
|---|---|---|---|---|---|
| H-01 | Raspberry Pi 4B | 4 GB RAM, 64-bit ARM Cortex-A72 | 1 | Boot to OS, confirm SSH access | ___ |
| H-02 | Knowles MEMS Microphone | SPH0645LM4H, I2S interface, SNR ≥ 65 dB | 1 | Audio capture test (`arecord -d 5 test.wav`) | ___ |
| H-03 | IR Camera Module | OV5647 / CSI-2, 940 nm IR LEDs, 5 MP | 1 | Capture 10 frames in darkness, verify IR | ___ |
| H-04 | PoE+ Injector / Switch | IEEE 802.3at (25.5W), 48V→12V stepdown | 1 | Measure output voltage: 12V ±0.5V | ___ |
| H-05 | IP66 Weatherproof Enclosure | 220×170×110 mm, UV-resistant ABS | 1 | Inspect gasket seal, cable glands | ___ |
| H-06 | 15W Heatsink + Thermal Pad | Aluminium, 1.85°C/W thermal resistance | 1 | Attach to Pi SoC, verify contact | ___ |
| H-07 | MicroSD (Application) | 64 GB Class-10 A2, SurakshaEdge OS image | 1 | MD5 checksum of image verified | ___ |
| H-08 | Ethernet Cable (shielded) | Cat 6A, STP, 10m (or length as needed) | 1 | Continuity test passed | ___ |

### 3.2 Software Pre-Flight

| # | Check | Command / Method | Expected Result | Pass? |
|---|---|---|---|---|
| S-01 | OS version | `uname -a` | Linux 6.1.x aarch64 | ___ |
| S-02 | SurakshaEdge service | `systemctl status surakshaedge` | Active (running) | ___ |
| S-03 | Audio mode | `curl http://localhost:8000/health` | `audio_mode: mfcc_cnn` | ___ |
| S-04 | WebSocket heartbeat | `wscat -c ws://localhost:8000/ws/alerts` | Ping response ≤ 1s | ___ |
| S-05 | CAMERA_TAMPER watchdog | Kill camera process, wait 4s | Log shows CAMERA_TAMPER | ___ |
| S-06 | RAM-only buffer | `ls /var/lib/surakshaedge/` | Only config files; no audio/video | ___ |
| S-07 | DPDP consent notice | Check signage at node location | Physical sign present | ___ |
| S-08 | Encrypted transit | Check TLS cert or VPN tunnel active | HTTPS/WSS or VPN active | ___ |

---

## 4. 72-Hour Soak Protocol

### 4.1 Observation Slot Schedule

| Slot | Duration | Calendar Time (IST) | Primary Operator | Secondary Operator |
|---|---|---|---|---|
| **Slot A** | 24 h | Day 1, 08:00 → Day 2, 08:00 | Operator-1 | Operator-2 (standby) |
| **Slot B** | 24 h | Day 2, 08:00 → Day 3, 08:00 | Operator-2 | Operator-1 (standby) |
| **Slot C** | 24 h | Day 3, 08:00 → Day 4, 08:00 | Operator-1 | Operator-2 (standby) |

> **Handover Rule:** At every 24-hour handover, the outgoing operator briefs the incoming operator on pending alerts, any node anomalies, and the current false-positive count. The handover log is countersigned by both operators.

### 4.2 Rotation Details

| Time Block | Duty | Activity |
|---|---|---|
| 08:00–14:00 | Active Watch | Monitor dashboard; log all events in Data Sheet |
| 14:00–16:00 | Node Inspection Round | Physical walkthrough of all 5 nodes; check enclosures, cables |
| 16:00–20:00 | Active Watch | Monitor dashboard |
| 20:00–22:00 | Night-Mode Verification | Confirm IR cameras switching to night mode (ambient light < 10 lux) |
| 22:00–08:00 | Overnight Monitoring (standby) | Automated logging; standby operator on-call within 15 minutes |

### 4.3 Node Health Checks (Every 6 Hours)

For each node, record in the Data Sheet:
- CPU temperature (target: < 70°C sustained)
- RAM usage (baseline + hourly growth)
- Process uptime (`ps aux | grep surakshaedge`)
- Alert count since last check
- False-positive count since last check

### 4.4 Synthetic Scenario Injections

During each slot, the following **controlled test events** must be injected to verify system response (coordinate with security team; use designated test actors):

| Scenario | Slot | Node | Expected System Response |
|---|---|---|---|
| Aggressive push (chest shove) | A | N1 | ALERT within ≤ 89.4ms |
| Prolonged hug (friendly) | A | N3 | No alert (K_t < threshold) |
| Night assault simulation | B | N4 | ALERT; IR camera active |
| Crowd occlusion (10+ persons) | B | N2 | ADVISORY or ALERT (not missed) |
| Camera tampering (cover lens) | C | N5 | CAMERA_TAMPER event within 3s |
| Memory stress (8h continuous) | C | All | RAM growth < 10 MB/hr |

---

## 5. Performance Targets & Acceptance Criteria

> [!IMPORTANT]
> All five targets must be met for Stage-IV sign-off. Each target is measured independently per node and aggregated.

### 5.1 Metric Definitions & Targets

| Metric ID | Metric | Target | Measurement Method | Failure Action |
|---|---|---|---|---|
| **PT-01** | Alert Latency (sensor-to-screen) | ≤ **89.4 ms** (p95) | Timestamp delta: `audio_capture_ts` → `websocket_push_ts` | Inspect network; check pipeline bottleneck |
| **PT-02** | False Positive Rate | < **2 per 8-hour shift** per node | Manual review of operator-flagged FPs in Data Sheet | Review temporal gate Δt threshold |
| **PT-03** | Camera Uptime | ≥ **99.5% per 24h window** | `(1 - downtime_minutes/1440) × 100` per node per day | Inspect cable, enclosure; restart service |
| **PT-04** | Memory Growth Rate | < **10 MB/hr** | `RSS(t+1h) - RSS(t)` via `/proc/<pid>/status` | Check for audio/video buffer leak; restart |
| **PT-05** | Operator Response Time | ≤ **30 seconds** alert-to-acknowledgement | Operator logs acknowledgement time in Data Sheet | Provide UX remediation; re-train operator |
| **PT-06** | CAMERA_TAMPER Detection | ≤ **3 seconds** to log event | Inject tamper; measure time to watchdog log entry | Reduce heartbeat interval in config |

### 5.2 Empirical Baselines (from pre-field bench tests)

| Metric | Bench Value | Field Target | Source |
|---|---|---|---|
| Alert latency p50 | 54.8 ms | ≤ 89.4 ms p95 | `results/Benchmark_Execution_Logs.txt` |
| Alert latency p95 | 89.4 ms | ≤ 89.4 ms | Empirical baseline |
| Memory growth | 6.2 MB/hr (idle) | < 10 MB/hr | Bench soak test, 8h run |
| False positives | 0.8/shift (lab) | < 2/shift | Lab validation dataset |

---

## 6. Operator Usability Rubric

Each security-guard operator completes this 10-point rubric at the **end of each 24-hour slot**. Scale: 1 (poor) → 5 (excellent). Target average: **≥ 3.5 / 5.0**.

**OPERATOR FEEDBACK FORM — SurakshaEdge Field Trial**
*Node Watched:* ___________ *Slot:* ___________ *Date:* ___________
*Operator Name:* ___________ *Shift Duration:* ___________ hours

---

| # | Question | Rating (1–5) | Comments |
|---|---|---|---|
| U-01 | The alert sound/visual was immediately noticeable | ___ | |
| U-02 | The dashboard map correctly identified the incident location | ___ | |
| U-03 | I could acknowledge an alert within 30 seconds without guidance | ___ | |
| U-04 | The alert included enough information to decide on escalation | ___ | |
| U-05 | False alarms were infrequent and I could dismiss them easily | ___ | |
| U-06 | The system worked reliably through my entire shift | ___ | |
| U-07 | Night-mode camera images were clear enough to assess the situation | ___ | |
| U-08 | I felt confident this system would help me respond faster | ___ | |
| U-09 | I would recommend this system to our security management | ___ | |
| U-10 | Overall system usability rating | ___ | |

**Total Score:** ___ / 50 &emsp; **Average:** ___ / 5.0

**Additional Comments (open text):**
```
________________________________________________________________________
________________________________________________________________________
________________________________________________________________________
```

**Operator Signature:** _________________________ **Date:** ___________

---

## 7. DPDP Act 2023 Compliance Checklist

> [!IMPORTANT]
> The Digital Personal Data Protection Act 2023 (DPDP Act) governs all personal data processing in India. All 8 items below must be checked BEFORE the trial begins. Any unchecked item is a **blocker**.

| # | DPDP Requirement | Implementation in SurakshaEdge | Verified? | Verifier |
|---|---|---|---|---|
| **D-01** | **Data Minimisation** — Collect only what is necessary | Audio: 2.56s rolling window, discarded post-inference. Video: skeletal keypoints only (no raw frame stored). | ☐ | ___ |
| **D-02** | **RAM-Only Buffer** — No persistent personal data storage | Audio and video frames reside exclusively in `collections.deque` in-process RAM; `ls /var/lib/surakshaedge/` confirms no `.wav`/`.jpg` files. | ☐ | ___ |
| **D-03** | **No PII Storage** — No identity-linked data persisted | Event log stores only: `{timestamp, node_id, event_type, K_t, S_t}`. No face images, voice recordings, or identity tokens stored. | ☐ | ___ |
| **D-04** | **Right to Erasure** — Mechanism to delete event records | `/api/v1/events/purge` endpoint (requires admin token) erases the SQLite events DB. Documented in `docs/API_REFERENCE.md`. | ☐ | ___ |
| **D-05** | **Consent Notice** — Visible notice at each node location | Physical A4 sign at each node: "AI-based safety monitoring in operation. Data processed in real-time and not stored. Contact: [DPO email]." | ☐ | ___ |
| **D-06** | **Encrypted Transit** — Data in motion protected | All WebSocket streams use WSS (TLS 1.3) on campus network. API uses HTTPS with self-signed cert or VPN tunnel. | ☐ | ___ |
| **D-07** | **Audit Log** — Record of all system access and alerts | FastAPI access log + alert event log in SQLite. Logs rotated daily; retained 30 days (minimum DPDP period). | ☐ | ___ |
| **D-08** | **DPO Contact** — Data Protection Officer identified and reachable | DPO: Institution Coordinator (see Section 10 sign-off). Contact email displayed on consent notice at all nodes. | ☐ | ___ |

**Compliance Certification:**
I certify that all 8 DPDP Act 2023 compliance items have been verified and are in place for the duration of the field trial.

Signed: _________________________ Role: __________________ Date: ___________

---

## 8. Incident Response Procedure

### 8.1 When an ALERT Fires

```
┌────────────────────────────────────────────────────────────┐
│  SURAKSHAEDGE ALERT RESPONSE PROCEDURE                     │
│                                                            │
│  T+0s   : Dashboard displays ALERT banner + audio tone     │
│  T+0–30s : Operator views camera feed + event details      │
│  T+30s  : DECISION POINT                                  │
│            ├─► FALSE POSITIVE → Click "Dismiss" button     │
│            │   Log: timestamp, node_id, reason code        │
│            └─► REAL INCIDENT → Click "Escalate" button     │
│                                                            │
│  T+30–60s : Real Incident Escalation Chain                 │
│    Step 1: Radio/Call shift supervisor                     │
│    Step 2: Supervisor dispatches guard to location         │
│    Step 3: If confirmed → Call campus emergency: ext. 100  │
│    Step 4: Notify faculty-on-duty within 5 minutes         │
│    Step 5: Document in incident log (physical register)    │
│    Step 6: Preserve dashboard screenshot (Ctrl+P → PDF)    │
│                                                            │
│  T+60–120s : If no guard available                        │
│    → Call local police: 112                               │
│    → Activate campus PA announcement                      │
└────────────────────────────────────────────────────────────┘
```

### 8.2 Escalation Chain

| Level | Role | Contact Method | Response Time Target |
|---|---|---|---|
| L1 | Security Guard (on duty) | Direct observation | Immediate |
| L2 | Shift Supervisor | Radio / WhatsApp | ≤ 2 minutes |
| L3 | Faculty-on-Duty | Phone | ≤ 5 minutes |
| L4 | Head of Security | Phone | ≤ 10 minutes |
| L5 | Campus Administration | Phone | ≤ 15 minutes |
| L6 | Emergency Services (112) | Direct call | As needed |

### 8.3 System Failure Response

| Failure Mode | Symptoms | Immediate Action |
|---|---|---|
| Node goes offline | Dashboard shows node grey/disconnected | Physical inspection; restart `surakshaedge` service |
| All alerts silent (> 30 min) | No events despite expected activity | Check WebSocket connection; restart API server |
| False positive storm (> 10 in 1hr) | Excessive alerts | Temporarily increase K_t threshold via config; notify student lead |
| CAMERA_TAMPER event | Tamper warning on dashboard | Physical inspection of node enclosure; check for vandalism |
| Memory alert (> 10 MB/hr growth) | System slowdown, potential OOM | Restart pipeline process; collect heap dump for analysis |

---

## 9. Data Collection Sheet

### 9.1 Event Log Template

Operators record every system-generated event and manual observation in the table below. One row per event. Continue on additional sheets as needed.

**Sheet Header:**
- Node Monitored: ___________
- Operator: ___________
- Slot: A / B / C
- Date: ___________

| # | Timestamp (IST) | Node ID | Event Type | K_t Score | S_t Score | Operator Response Time (s) | Operator Action | False Positive? (Y/N) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | | |
| 2 | | | | | | | | | |
| 3 | | | | | | | | | |
| 4 | | | | | | | | | |
| 5 | | | | | | | | | |
| 6 | | | | | | | | | |
| 7 | | | | | | | | | |
| 8 | | | | | | | | | |
| 9 | | | | | | | | | |
| 10 | | | | | | | | | |
*(Extend as needed)*

**Event Type Codes:**
- `ALERT` — System-generated assault alert (K_t ≥ threshold AND S_t ≥ threshold)
- `ADVISORY` — Single-modality warning (audio-only or vision-only)
- `CAMERA_TAMPER` — Camera heartbeat watchdog triggered
- `SYNTHETIC` — Controlled test scenario injection
- `NODE_RESTART` — Node service restart event
- `HANDOVER` — Operator shift handover

### 9.2 24-Hour Summary Sheet

Complete at the end of each 24-hour slot:

| Slot | Total Events | ALERT Count | ADVISORY Count | Confirmed Incidents | False Positives | FP Rate / Shift | Avg Latency (ms) | Max RAM Growth (MB/hr) | Camera Uptime (%) | Operator Avg Score |
|---|---|---|---|---|---|---|---|---|---|---|
| A (Day 1) | | | | | | | | | | |
| B (Day 2) | | | | | | | | | | |
| C (Day 3) | | | | | | | | | | |
| **TOTAL** | | | | | | | | | | |

### 9.3 Hardware Serial Number Register

| Node | Pi Serial | Camera S/N | Mic Batch | Enclosure S/N | PoE Injector S/N |
|---|---|---|---|---|---|
| N1 | | | | | |
| N2 | | | | | |
| N3 | | | | | |
| N4 | | | | | |
| N5 | | | | | |

---

## 10. Sign-Off Box

By signing below, each party certifies that the 72-hour SurakshaEdge Field Trial was conducted in accordance with this protocol, that all performance targets were met, and that the DPDP Act 2023 compliance checklist was verified.

---

**Institution Coordinator**

Name: _________________________________________________

Designation: _________________________________________________

Signature: _________________________ Date: ___________

---

**Faculty Mentor**

Name: _________________________________________________

Department: _________________________________________________

Signature: _________________________ Date: ___________

---

**Student Lead**

Name: **Shambhu Kumar Shekhar Sinha**

Roll Number: _________________________________________________

Signature: _________________________ Date: ___________

---

**Ethics Officer / DPDP Compliance Officer**

Name: _________________________________________________

Designation: _________________________________________________

Signature: _________________________ Date: ___________

---

**Trial Outcome (Circle One):** &emsp; **PASSED** &emsp; / &emsp; **CONDITIONAL PASS** &emsp; / &emsp; **FAILED**

**Conditional Pass Notes (if applicable):**
```
________________________________________________________________________
________________________________________________________________________
```

---

*Document Version: 1.0 | Prepared under GNIOT Ethics Board Protocol | SurakshaEdge Stage-IV Field Validation*
