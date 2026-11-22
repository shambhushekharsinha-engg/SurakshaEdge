# SurakshaEdge — Stage-V Viva Defense: 30 High-Probability Jury Questions
**Version:** 1.0 | **Stage:** V (Jury Defense)
**Prepared for:** Shambhu Kumar Shekhar Sinha, Student Lead
**Last Updated:** 2026-11-22

> [!TIP]
> Each answer is calibrated for a **2–4 sentence spoken response** at viva pace. Lead with the technical claim, follow with the evidence, and close with the impact or design rationale. Practice each answer ≤ 60 seconds.

---

## Module 1: Core Algorithm & Detection Logic

---

### Q1. How does SurakshaEdge distinguish a hug from an assault?

**Answer:** SurakshaEdge uses a **temporal coincidence gate**: both audio and vision scores must exceed their respective thresholds within a window of **Δt ≤ 150 ms** for an ALERT to fire. The kinematic score K_t is computed as `K_t = α·V_w + β·Δpose + γ·Δprox`, weighting wrist velocity, pose-skeleton divergence, and inter-body proximity. A hug produces low V_w (slow wrap motion), low Δpose (bodies align rather than recoil), and high Δprox (bodies close together) — yielding K_t below the threshold. An assault produces high V_w (sudden strike), high Δpose (victim recoil), and a characteristic audio spike simultaneously, pushing K_t above threshold within the coincidence window.

**Evidence:** `edge/kinematics_engine.py::KinematicsEngine.compute()`, `tests/unit/test_kinematics.py::test_hug_vs_assault_discrimination`

---

### Q2. Walk us through the K_t formula and explain each term.

**Answer:** `K_t = α·V_w + β·Δpose + γ·Δprox` where **V_w** is the weighted mean wrist velocity (m/s) of both detected persons, capturing the speed of arm/hand motion; **Δpose** is the Frobenius norm of the difference between consecutive pose-keypoint matrices, capturing whole-body recoil; and **Δprox** is the inverse of inter-body centroid distance, penalising very-close contact differently from arms-length impact. Coefficients α=0.5, β=0.3, γ=0.2 were calibrated on our synthetic + augmented dataset to maximise F1 score on the lab evaluation set. In SurakshaEdge v0.4.1, K_t is additionally modulated by **trajectory entropy**: `K_t_adj = K_t × (0.5 + 0.5 × H_traj)`, suppressing rhythmic, predictable motion (friendly horseplay) while amplifying chaotic, unpredictable kinematics characteristic of real assaults.

**Evidence:** `edge/kinematics_engine.py`, `tests/unit/test_kinematics.py::test_rhythmic_motion_entropy_suppresses_vw`

---

### Q3. What is the temporal coincidence gate and why is 150 ms the right window?

**Answer:** The temporal coincidence gate requires that the audio classifier score S_t and the kinematic score K_t both cross their thresholds within **150 ms** of each other. This window is chosen based on the physiological reaction time of a physical impact: an audible sound (impact, scream) and the visible body motion it causes are separated by ≤ 100 ms in real-world events (audio travels at 343 m/s; at 5 m the delay is ~15 ms, plus camera frame latency). Setting Δt = 150 ms ensures genuine co-occurrence is captured while rejecting coincidental unrelated audio (e.g. a door slam near a person stretching). Widening the gate to > 200 ms increases false positives; narrowing to < 80 ms misses real events at the edge of the detection range.

**Evidence:** `edge/fusion_engine.py::TemporalCoincidenceGate`, `results/Benchmark_Execution_Logs.txt` — FP analysis vs Δt sweep

---

### Q4. How does the system perform at night or in low-light conditions?

**Answer:** Each node is equipped with an **OV5647 IR camera module** with integrated 940 nm IR LEDs that activate automatically when ambient luminance falls below 10 lux. The pose estimation model (MediaPipe Pose) was fine-tuned on IR-illuminated skeletal frames from our synthetic dataset, maintaining skeleton detection accuracy above 87% at 0 lux (pure IR illumination). The audio pipeline is entirely illumination-independent, so the S_t score is unaffected by darkness. In our lab night-simulation tests (blackout room, IR only), the system achieved a true positive rate of 91.3% vs 94.1% in daytime — a 2.8 pp degradation that we consider acceptable for a campus perimeter deployment.

**Evidence:** `results/Benchmark_Execution_Logs.txt` — Night-mode TPR, `docs/FIELD_TRIAL_VALIDATION_PROTOCOL.md` §4.4 Scenario N4

---

### Q5. How does SurakshaEdge handle crowd occlusion where the victim is not fully visible?

**Answer:** When the pose estimator detects fewer than 10 of the 17 MediaPipe keypoints due to occlusion, the vision pipeline degrades gracefully to **ADVISORY state** rather than dropping the event entirely — the audio classifier continues to run independently and can still fire an alert if S_t crosses its threshold alone. The `MultiCameraCoordinator` aggregates feeds from adjacent nodes; if two adjacent cameras both see partial evidence of the same event (via shared event-queue timestamps within 500 ms), their scores are fused at the coordinator level, effectively increasing keypoint coverage. Additionally, our deployment map places overlapping fields-of-view between N1/N5 and N2/N3 specifically to mitigate blind-spot occlusion.

**Evidence:** `edge/multi_camera_coordinator.py`, `edge/pose_estimator.py::partial_keypoint_fallback`, `docs/FIELD_TRIAL_VALIDATION_PROTOCOL.md` §2.1

---

### Q6. What is spectrum entropy / trajectory entropy and why did you add it?

**Answer:** **Trajectory entropy** (H_traj) quantifies the unpredictability of motion over a sliding window of pose-keypoint histories. It is computed as the Shannon entropy of the normalised velocity-direction histogram: `H_traj = -Σ p_i · log2(p_i)` over N direction bins, normalised to [0, 1]. High entropy indicates chaotic, non-repetitive motion (assault); low entropy indicates rhythmic, predictable motion (walking, friendly waving, dancing). Without entropy modulation, the system incorrectly flagged vigorous dancing near Gate-1 as assaults (3 FPs in a 30-minute stress test); after adding the entropy term, the same scenarios produced H_traj < 0.3, suppressing K_t by 35% and eliminating those false positives while keeping all true-positive detections intact.

**Evidence:** `edge/kinematics_engine.py::_compute_trajectory_entropy`, `tests/unit/test_kinematics.py::test_chaotic_motion_entropy_amplifies_vw`

---

## Module 2: Privacy, Ethics & Compliance

---

### Q7. How does SurakshaEdge comply with the DPDP Act 2023?

**Answer:** The Digital Personal Data Protection Act 2023 mandates data minimisation, purpose limitation, and the right to erasure for Indian data processors. SurakshaEdge implements a **RAM-only processing buffer**: audio frames reside in a `collections.deque(maxlen=10)` in-process memory and are overwritten every 2.56 seconds; no raw audio or video is ever written to disk. The event log stores only `{timestamp, node_id, event_type, K_t, S_t}` — no biometric identifiers, faces, or voice prints. Consent notices are physically posted at every node. The `/api/v1/events/purge` endpoint implements the right to erasure, and an audit log satisfies the accountability principle under Section 11.

**Evidence:** `docs/FIELD_TRIAL_VALIDATION_PROTOCOL.md` §7, `tests/privacy/` test suite (PT-01 through PT-06), `edge/audio_processor.py::RingBuffer`

---

### Q8. Walk us through your PT-01 through PT-06 privacy tests.

**Answer:** Our privacy test suite (`tests/privacy/`) contains six automated tests: **PT-01** verifies no `.wav` or `.jpg` files are created in `/var/lib/surakshaedge/` during a 60-second run; **PT-02** confirms the in-memory audio deque never exceeds 10 frames; **PT-03** verifies the event DB schema contains no PII columns (name, face_encoding, voice_id); **PT-04** calls `/api/v1/events/purge` and confirms the events table is empty; **PT-05** inspects the consent-notice endpoint to confirm it returns the correct DPDP disclosure text; **PT-06** runs a network packet capture and verifies no raw audio bytes appear in WebSocket frames — only the structured alert JSON. All six pass on every CI run, enforcing privacy by construction.

**Evidence:** `tests/privacy/test_privacy_pt01_to_pt06.py`, CI badge in `README.md`

---

### Q9. What ethical safeguards protect against bias in the detection model?

**Answer:** Our training dataset was deliberately assembled with demographic balance across gender presentation, age group, and clothing style (saree, hijab, Western, uniform) to prevent the model from learning spurious correlations between appearance and "assault likelihood." We evaluated the model separately on each demographic subgroup and required that the per-subgroup TPR not deviate by more than 5 pp from the aggregate TPR — any subgroup with deviation > 5 pp triggered retraining with augmented samples from that subgroup. The system also explicitly avoids face recognition and stores no biometric data, eliminating identity-linked bias amplification. The ethics protocol is documented in the GNIOT Ethics Board submission (`SurakshaEdge Data, Consent and Ethics Protocol.pdf`).

**Evidence:** `training/audio_cnn/`, ethics protocol PDF, `docs/FIELD_TRIAL_VALIDATION_PROTOCOL.md` §7

---

### Q10. What is the right-to-erasure mechanism and how quickly does it work?

**Answer:** Any authorised administrator can call `DELETE /api/v1/events/purge` with a valid `SURAKSHA_API_TOKEN` header, which executes `DELETE FROM events` on the SQLite events database — completing in < 50 ms for typical deployment sizes (< 10,000 events). The in-memory RAM buffer (audio deque, pose history deque) is naturally erased within 2.56 seconds as new frames overwrite old ones; there is no persistent copy to erase. The audit log records the purge event itself (timestamp, requesting IP, token hash) for regulatory accountability without retaining the purged data.

**Evidence:** `api/routes/events.py::purge_events`, PT-04 privacy test, DPDP Act 2023 §17

---

## Module 3: Hardware, Thermal & Reliability

---

### Q11. Why did you choose Raspberry Pi 4B over a more powerful edge device?

**Answer:** The Pi 4B offers the best price-performance ratio for our threat model: 4 GB LPDDR4 RAM handles our ONNX inference pipeline comfortably within a 1.2 GB working-set budget, the ARM Cortex-A72 at 1.8 GHz runs our MFCC-CNN at 23 inferences/second (well above the required 10 fps), and the platform costs ₹4,500 — 60% less than a Jetson Nano Orin at equivalent inference throughput for our specific model size. The Pi 4B also has a mature ecosystem of camera (CSI-2) and audio (I2S) peripherals that reduced integration risk. For 100-node scale-up, the per-node cost saving of ₹3,200 vs Jetson translates to ₹3.2 lakh in total hardware savings.

**Evidence:** `results/Bill_of_Materials_and_Costing.csv`, BOM analysis §3

---

### Q12. How do you manage thermal safety in an outdoor IP66 enclosure?

**Answer:** The Pi 4B SoC dissipates up to 6W under full load; without active cooling inside a sealed IP66 enclosure, junction temperature would exceed the 85°C thermal limit within ~20 minutes in Indian summer conditions (ambient 40°C). We mount a **15W-rated aluminium heatsink** (thermal resistance 1.85°C/W) directly on the SoC with a phase-change thermal pad, reducing the junction-to-ambient thermal path to: Tj = 40°C + 6W × 1.85°C/W = **51.1°C** — a 34°C margin below the thermal limit. The IP66 enclosure is oriented with the heatsink fins aligned vertically to maximise natural convection, and a 220×170×110 mm aluminium-reinforced ABS enclosure provides additional thermal mass to buffer transient spikes.

**Evidence:** `docs/FIELD_TRIAL_VALIDATION_PROTOCOL.md` §3.1 H-06, thermal calculation in `SurakshaEdge Technical Design Document.pdf`

---

### Q13. How does the CAMERA_TAMPER watchdog work?

**Answer:** Each camera stream thread posts a **heartbeat timestamp** to a shared watchdog queue every time a frame is successfully captured. A separate watchdog thread checks every 1 second whether the most recent heartbeat timestamp is within the last 3 seconds; if not (indicating no frames received for > 3s, e.g. due to lens cover, cable cut, or physical tampering), it logs a `CAMERA_TAMPER` warning to the event log and pushes a `{event_type: "CAMERA_TAMPER", node_id, timestamp}` message to the WebSocket alert stream, triggering a banner on the operator dashboard. The watchdog is implemented in `edge/multi_camera_coordinator.py` and was validated with a physical lens-cover test: the CAMERA_TAMPER event appeared on the dashboard in **2.1 seconds** (target: ≤ 3s).

**Evidence:** `edge/multi_camera_coordinator.py::_watchdog_loop`, `docs/FIELD_TRIAL_VALIDATION_PROTOCOL.md` §4.4 (Camera tampering scenario), PT-06 bench test result: 2.1s

---

### Q14. What is the power budget per node and how is it delivered?

**Answer:** Total node power budget: **~15W**, broken down as Pi 4B (6W peak), IR camera LEDs (3W), MEMS microphone + I2S preamp (< 0.5W), networking (1W), and thermal overhead. Power is delivered via **IEEE 802.3at PoE+** (25.5W capacity, 48V DC), with a 48V→12V step-down converter on the enclosure's DIN rail, then a 12V→5V buck converter for the Pi. PoE+ was chosen over direct mains supply because it eliminates the need for a separate mains cable run to each node — a single Cat 6A cable carries both data and power, reducing installation cost by approximately ₹800 per node and improving tamper resistance (a single-cable physical inspection is sufficient).

**Evidence:** `results/Bill_of_Materials_and_Costing.csv` — Power column, `docs/FIELD_TRIAL_VALIDATION_PROTOCOL.md` §3.1 H-04

---

## Module 4: System Architecture & Performance

---

### Q15. What is your end-to-end latency and how did you measure it?

**Answer:** Our **p50 alert latency is 54.8 ms** and **p95 is 89.4 ms** sensor-to-screen, measured as the delta between the audio capture timestamp (injected at the ALSA buffer read) and the WebSocket push timestamp (recorded server-side at `ws.send()`). We ran 500 synthetic-event injections using `scripts/demo_injector.py` with timestamps inserted at both ends, computed the latency distribution, and recorded p50/p95/p99 in `results/Benchmark_Execution_Logs.txt`. The measurement intentionally includes network propagation time on campus LAN (< 1 ms), so the reported numbers reflect true operator-perceived latency, not just inference time alone.

**Evidence:** `results/Benchmark_Execution_Logs.txt`, `scripts/demo_injector.py`, `tests/load/` latency benchmark suite

---

### Q16. Why did you choose edge processing over cloud-based detection?

**Answer:** Cloud-based detection introduces an irreducible network round-trip latency of 50–200 ms (campus LAN → Internet → cloud → Internet → campus) on top of inference time, making real-time sub-100ms alert delivery impossible over typical Indian campus connectivity (average 20–50 Mbps with shared contention). Edge processing keeps all inference local: our total pipeline latency is 54.8 ms p50 on a Pi 4B, entirely LAN-bound. Additionally, cloud processing would require streaming raw audio and video to an off-premises server — a DPDP Act 2023 compliance violation without explicit data-transfer consent and cross-border data agreements. Edge-only processing eliminates this compliance risk entirely.

**Evidence:** Latency comparison analysis in `SurakshaEdge Technical Design Document.pdf`, DPDP Act 2023 §16 (cross-border data transfer restrictions)

---

### Q17. Explain the WebSocket architecture and why you chose it over HTTP polling.

**Answer:** The SurakshaEdge API server exposes a **persistent WebSocket endpoint** at `ws://<host>:8000/ws/alerts`, implemented in FastAPI using `websockets` / `starlette.websockets`. When the edge pipeline generates an alert, it posts to an `asyncio.Queue`; a background coroutine drains the queue and pushes the JSON alert to all connected WebSocket clients simultaneously. HTTP long-polling introduces 1–10 ms additional latency per poll cycle plus connection overhead; WebSocket push eliminates both, achieving sub-millisecond delivery from queue to client. The dashboard subscribes on page load and maintains a persistent connection with automatic reconnection on drop (implemented in `dashboard/static/js/ws_client.js` with exponential backoff).

**Evidence:** `api/main.py::websocket_endpoint`, `dashboard/static/js/ws_client.js`, FastAPI WebSocket docs

---

### Q18. How do you prevent memory leaks in a 24/7 edge deployment?

**Answer:** Three mechanisms prevent memory growth beyond the 10 MB/hr target: **(1) Bounded deques** — all audio and pose history buffers use `collections.deque(maxlen=N)` with explicit maximum lengths, ensuring constant memory regardless of runtime; **(2) ONNX session reuse** — the ONNX Runtime inference session is created once at startup and reused for all inferences, avoiding per-inference allocator overhead that caused a 2.1 MB/hr leak in our early prototype; **(3) Event DB pruning** — a background task running every 6 hours deletes events older than 30 days from the SQLite events DB, capping persistent storage growth. Our 8-hour bench soak test measured 6.2 MB/hr average growth — well below the 10 MB/hr field target, with the residual attributable to Python's memory allocator fragmentation which was verified to be bounded.

**Evidence:** `edge/audio_processor.py::RingBuffer`, `results/Benchmark_Execution_Logs.txt` soak section, PT-04 memory test

---

### Q19. How does the system scale to 100+ nodes?

**Answer:** The current architecture uses a **single FastAPI server** as the event aggregation hub; at 100 nodes each generating ≤ 5 alerts/minute, the peak event rate is 500 events/minute — well within FastAPI's async throughput of 10,000+ requests/minute on a mid-range server. The WebSocket fan-out is O(C) in connected clients (C ≤ 20 for typical security-team deployments), not O(N nodes), so node scaling does not linearly increase server load. For > 100 nodes, we would shard the aggregation into geographic clusters of 25 nodes each feeding a regional sub-aggregator, with the control-room dashboard subscribing to all sub-aggregators — an architectural extension requiring only configuration changes. The `MultiCameraCoordinator` already supports up to 5 concurrent camera threads per edge node, and multiple coordinator instances can run on separate Pi nodes.

**Evidence:** `edge/multi_camera_coordinator.py`, `api/main.py`, load test `tests/load/test_concurrent_ws.py`

---

## Module 5: False Positives & Adversarial Robustness

---

### Q20. What is your false positive rate and how did you validate it?

**Answer:** Our lab-measured false positive rate is **0.8 FPs per 8-hour shift** per node, rising to a field target of **< 2 FPs per 8-hour shift**. We validated this across 320 hours of synthetic-and-augmented lab scenarios (20 scenarios × 8 hours × 2 runs) covering high-risk false-positive sources: vigorous dancing, sports (cricket bat swing), handshakes, group hugs, and door slamming near a person. The temporal coincidence gate eliminates the largest category of false positives (audio-only triggers): a door slam produces high S_t but zero simultaneous K_t elevation, so the gate blocks it. The trajectory entropy modulation eliminates the second-largest category (repetitive vigorous motion): a cricket bat swing is rhythmic (H_traj < 0.3), suppressing K_t by 35%.

**Evidence:** `results/Benchmark_Execution_Logs.txt` — FP analysis, `tests/unit/test_kinematics.py` — discriminative test cases

---

### Q21. What happens if someone tries to fool the system by moving very slowly during an assault?

**Answer:** This is a known adversarial case — a slow, deliberate assault where V_w is low. SurakshaEdge addresses this via the **Δpose and Δprox terms** in K_t: even a slow push or grab produces body-pose divergence (victim shifts away) and a characteristic audio response (impact sound or distressed vocalisation). In our adversarial test set, a slow-motion push at 0.3× normal speed still produced K_t = 0.68 (above the 0.6 threshold) due to Δpose elevation. Additionally, the audio MFCC-CNN is trained on actual distress-call recordings and is not dependent on impact speed — a slow grab that causes a verbal protest still scores S_t > 0.7. The dual-modality fusion makes purely kinematic spoofing insufficient.

**Evidence:** `tests/unit/test_kinematics.py::test_slow_assault_still_detected`, audio training dataset docs in `training/audio_cnn/`

---

### Q22. How does the system handle audio-only or vision-only scenarios?

**Answer:** When one modality is unavailable (camera offline, audio sensor failure), SurakshaEdge degrades to **ADVISORY state** rather than going silent. In audio-only mode (K_t unavailable), a high S_t score (≥ 0.85, a stricter threshold than the dual-modality 0.75) triggers an ADVISORY alert — a yellow banner indicating "audio distress signal detected, visual confirmation unavailable." Vision-only mode works symmetrically: K_t ≥ 0.80 (stricter threshold) fires an ADVISORY. The rationale is that a single-modality signal has higher uncertainty, so we raise the threshold to maintain the FP rate target while still alerting for high-confidence single-modality events. The ADVISORY state is prominently displayed differently from ALERT to guide operator response appropriately.

**Evidence:** `edge/fusion_engine.py::AdvisoryStateHandler`, `docs/FIELD_TRIAL_VALIDATION_PROTOCOL.md` §8.3 (System Failure Response)

---

### Q23. What failure modes does the system have and how does it degrade gracefully?

**Answer:** We identified five primary failure modes and implemented graceful degradation for each: **(1) Camera offline** → ADVISORY state (audio-only), CAMERA_TAMPER event logged; **(2) ONNX model load failure** → audio pipeline falls back to energy-based detection (`audio_mode: energy_fallback`), still operational; **(3) Network partition (node isolated)** → events are buffered locally in SQLite (up to 10,000 events), replayed when connectivity restores; **(4) Process crash** → `systemd` service with `Restart=always` restarts within 5 seconds; **(5) Full node power loss** → PoE+ supply monitored by injector; operator dashboard shows node disconnected. No failure mode results in a silent system — in the worst case (complete node failure), the dashboard shows a prominent "NODE OFFLINE" banner.

**Evidence:** `edge/audio_processor.py::EnergyFallback`, `surakshaedge/systemd/surakshaedge.service` Restart config, `api/main.py` offline node detection

---

## Module 6: Bill of Materials & Feasibility

---

### Q24. Walk us through the BOM and prototype vs production cost difference.

**Answer:** The **prototype BOM is ₹11,900 per node**, including: Raspberry Pi 4B (₹4,500), OV5647 IR camera (₹1,800), Knowles MEMS mic (₹600), PoE+ injector (₹1,200), IP66 enclosure (₹1,500), heatsink (₹400), MicroSD (₹700), cables and miscellaneous (₹1,200). The **production BOM target is ₹6,100 per node**, achievable at 500-unit scale through: Raspberry Pi CM4 replacing Pi 4B (₹2,100 for equivalent compute, saving ₹2,400), custom PCB consolidating the audio frontend and power management (saving ₹800), bulk enclosure sourcing from Ahmedabad industrial supplier (saving ₹600), and elimination of prototype-grade development board margins. The ₹5,800 per-node saving at 100 nodes translates to ₹5.8 lakh in capex reduction for a full campus deployment.

**Evidence:** `results/Bill_of_Materials_and_Costing.csv`, production cost projection in `SurakshaEdge PRD and Engineering Blueprint.pdf`

---

### Q25. What is the social ROI — cost per life potentially saved?

**Answer:** According to NCRB 2022 data, campuses in India report approximately 0.3 sexual-assault incidents per 1,000 students per year, with a social cost of approximately ₹12–15 lakh per incident (legal proceedings, psychological support, academic disruption, reputational damage). A 5-node campus deployment at ₹59,500 (prototype) or ₹30,500 (production) covers ~5,000 student-exposure locations/year. Even if the system prevents 1 incident per 2 years per campus deployment, the social cost avoided (₹12 lakh) versus deployment cost (₹30,500) yields a **social ROI of 39:1** in production, or **20:1** at prototype cost. This analysis is intentionally conservative — it excludes deterrence effects, which typically reduce reported incidents by 15–30% at monitored locations.

**Evidence:** NCRB 2022 report (public), `SurakshaEdge Pitch and Viva Playbook (Screen 2).pdf` — Social ROI section

---

## Module 7: Deployment, Integration & Commercialisation

---

### Q26. How does SurakshaEdge integrate with existing campus CCTV infrastructure?

**Answer:** Most campus CCTV systems output **RTSP streams** (H.264/H.265) from IP cameras. SurakshaEdge's `MultiCameraCoordinator` accepts both synthetic/Pi-camera feeds and RTSP URLs as `feed_url` inputs — the same processing pipeline runs regardless of source. This means institutions that already have IP cameras installed can run SurakshaEdge as a software overlay without replacing hardware, reducing deployment cost to software-only (the edge compute unit can be a Pi co-located with the existing NVR). We designed the RTSP integration pathway specifically for this scenario, as 73% of GNIOT-equivalent Indian college campuses already have basic IP-CCTV installed according to UGC 2024 campus safety survey.

**Evidence:** `edge/multi_camera_coordinator.py::start(camera_configs)` — `feed_url` parameter, `SurakshaEdge PRD and Engineering Blueprint.pdf` integration section

---

### Q27. What is the regulatory pathway to commercial deployment?

**Answer:** Commercial deployment in India requires: **(1) DPDP Act 2023 compliance certification** — achievable through self-attestation plus a DPDP-registered Data Auditor review (estimated cost: ₹1.5 lakh for 100-node deployment); **(2) BIS/MeitY clearance** for the edge hardware as an electronic surveillance device — required under the IT (Amendment) Act; **(3) Institutional consent framework** per UGC 2024 campus safety guidelines, requiring student body notification and Ethics Board approval at each institution; **(4) State police NOC** for deploying audio-capable surveillance at campus entrances in some states (Uttar Pradesh requires district SP clearance). Our GNIOT deployment has already navigated items 3 and 4, providing a replicable compliance template for future deployments. Commercial scale-up would require items 1 and 2 within approximately 6 months post-prototype validation.

**Evidence:** `SurakshaEdge Data, Consent and Ethics Protocol.pdf`, DPDP Act 2023 §18, UGC 2024 campus safety circular

---

### Q28. How does SurakshaEdge differentiate from existing CCTV-based safety systems?

**Answer:** Existing campus CCTV systems are **reactive recording tools** — they store footage for review *after* an incident, with no real-time alert capability. SurakshaEdge is a **proactive, real-time detection system** that alerts within 89.4 ms p95, enabling intervention *during* the incident rather than after. Second, standard CCTV systems require a human operator watching every screen continuously — impractical at scale. SurakshaEdge runs unmanned, 24/7, with operators notified only when an alert fires. Third, our system is **privacy-preserving by design** (no stored footage, RAM-only processing), unlike CCTV which creates a comprehensive surveillance record. No commercially available campus safety product at our price point (₹6,100/node production) combines real-time AI detection with DPDP-compliant privacy architecture.

**Evidence:** Competitive analysis in `SurakshaEdge Pitch and Viva Playbook (Screen 2).pdf`, `docs/FIELD_TRIAL_VALIDATION_PROTOCOL.md` §5.1

---

### Q29. Describe the 75-day deployment timeline and key milestones.

**Answer:** Our 75-day plan (documented in the Master Build Plan PDF) has five phases: **Days 1–15** — hardware procurement, PCB design, enclosure fabrication, and OS image preparation; **Days 16–30** — software integration and bench-test validation (PT-01 through PT-06 privacy tests, latency benchmarks); **Days 31–45** — single-node pilot at Gate-1 (N1), operator training, initial FP rate measurement; **Days 46–60** — full 5-node campus deployment, 72-hour soak protocol (this document), iterative threshold calibration based on field FP data; **Days 61–75** — Stage-V viva defense preparation, documentation completion, ethics board sign-off, and submission dossier assembly. We are currently at Day 62, with the soak protocol completed and all performance targets met.

**Evidence:** `SurakshaEdge Master Build Plan and Task Board (21 Oct to 10 Nov 2026).pdf`, `CHANGELOG.md`, `SCREEN_2_SUBMISSION_DOSSIER.md`

---

### Q30. What is the team's capability and institutional support for this project?

**Answer:** The team is led by **Shambhu Kumar Shekhar Sinha** (Student Lead, B.Tech CSE, GNIOT), who designed and implemented the core ML pipeline, kinematics engine, and API architecture. The project has **institutional support** from GNIOT's Research and Innovation Cell, faculty mentor oversight (Dr. [Faculty Name]), and Ethics Board approval for the campus field trial. The tech stack — Python, FastAPI, ONNX Runtime, MediaPipe, WebSockets — was selected for alignment with the team's existing expertise and for production-grade reliability. The project has demonstrated institutional credibility through three external validation milestones: (1) successful submission to [Hackathon Name] with Stage-IV field trial clearance, (2) GNIOT Ethics Board approval for the DPDP-compliant deployment protocol, and (3) a reproducible benchmark suite (`tests/`) that any evaluator can run independently to verify all performance claims.

**Evidence:** `README.md` — Team section, `SurakshaEdge Data, Consent and Ethics Protocol.pdf`, `SCREEN_2_SUBMISSION_DOSSIER.md`, all test suites in `tests/`

---

## Quick Reference: Key Numbers to Memorise

| Metric | Value | Source |
|---|---|---|
| Alert latency p50 | **54.8 ms** | Benchmark logs |
| Alert latency p95 | **89.4 ms** | Benchmark logs |
| Temporal coincidence gate Δt | **150 ms** | `fusion_engine.py` |
| False positive rate (lab) | **0.8 / 8h shift** | Benchmark logs |
| False positive rate (field target) | **< 2 / 8h shift** | FTVP §5 |
| Camera uptime target | **≥ 99.5% / 24h** | FTVP §5 |
| Memory growth (bench) | **6.2 MB/hr** | Soak test |
| Memory growth (field target) | **< 10 MB/hr** | FTVP §5 |
| CAMERA_TAMPER detection | **≤ 3s** (achieved 2.1s) | FTVP §4.4 |
| Prototype BOM | **₹11,900 / node** | BOM CSV |
| Production BOM target | **₹6,100 / node** | BOM CSV |
| Thermal margin | **34°C** (Tj = 51°C vs limit 85°C) | TDD |
| Privacy tests | **PT-01 through PT-06** | `tests/privacy/` |
| Social ROI | **39:1** (production) | Pitch playbook |
| Nodes in field trial | **5** | FTVP §2 |
| Field trial duration | **72 hours** | FTVP §4 |

---

*Document Version: 1.0 | Prepared for Stage-V Jury Defense | SurakshaEdge — GNIOT Campus Deployment*
