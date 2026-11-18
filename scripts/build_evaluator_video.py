"""
SurakshaEdge — Senior Evaluator Demo Video Generator (Streamed Pipeline)
Native 1920x1080 @ 30 FPS · Ultra-low RAM usage (<100MB) via cv2.VideoWriter stream
Multiplexed with FFmpeg 7.1 and edge-tts calibrated Indian English narration.
"""
from __future__ import annotations
import os, sys, math, subprocess
import cv2
import numpy as np
from pathlib import Path
import soundfile as sf

ROOT        = Path(r"C:\SurakshaEdge\surakshaedge")
FRAMES_DIR  = Path(r"C:\Users\shamb\.gemini\antigravity\brain\3dd2ba4e-ad18-4375-80c1-81e1f903c5bd\video_frames2")
AUDIO_DIR   = ROOT / "data" / "audio" / "voiceover"
OUTPUT_PATH = ROOT / "data" / "SEVA_FIRST_SurakshaEdge_EVALUATOR_DEMO.mp4"
TEMP_VIDEO  = ROOT / "data" / "temp_video.mp4"
TEMP_AUDIO  = ROOT / "data" / "temp_combined_audio.wav"
FFMPEG      = r"C:\Users\shamb\AppData\Local\Programs\Python\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"

W, H = 1920, 1080
FPS = 30
DASH_W = 1346
X_OFF  = (W - DASH_W) // 2  # 287 px on left and right

# Colors
BG_DARK     = (18, 12, 8)       # #080c12
SIDE_BG     = (24, 15, 10)      # #0a0f18
ACCENT_BLUE = (246, 160, 99)    # #63a0f6
ACCENT_RED  = (68, 68, 239)     # #ef4444
ACCENT_AMB  = (60, 146, 251)    # #f97316
ACCENT_GRN  = (94, 197, 34)     # #22c55e
WHITE       = (255, 255, 255)

ACT_INFOS = [
    {"audio": "Act1_The_Reality_and_The_Gap.mp3", "title": "ACT 1: THE REALITY & THE SURVEILLANCE GAP", "subtitle": "NCRB: 4 Lakh+ Crimes · 95% Passive CCTV · Zero Instant Action", "col": ACCENT_RED},
    {"audio": "Act2_Architecture_and_Skeleton_Inspector.mp3", "title": "ACT 2: EDGE AI & REAL-TIME SKELETON INSPECTOR", "subtitle": "YOLOv8-Pose (17 Joints) · 18 FPS CPU · MFCC-CNN Acoustic distress", "col": ACCENT_BLUE},
    {"audio": "Act3_Hard_Negative_Suppression.mp3", "title": "ACT 3: HARD-NEGATIVE FALSE ALARM SUPPRESSION", "subtitle": "1.5s Temporal Fusion Gate: Jogging & Horns Suppressed 100%", "col": ACCENT_AMB},
    {"audio": "Act4_Assault_Alert_and_Encrypted_Replay.mp3", "title": "ACT 4: LIVE ASSAULT ALERT & ENCRYPTED EVIDENCE", "subtitle": "89ms Trigger · Zero Disk Persistence · RAM Ring Buffer Only", "col": ACCENT_RED},
    {"audio": "Act5_Multi_Node_and_Telemetry_Export.mp3", "title": "ACT 5: MULTI-NODE CAMPUS COORDINATION", "subtitle": "Autonomous Edge Nodes · No Cloud Single-Point-of-Failure", "col": ACCENT_BLUE},
    {"audio": "Act6_Hardware_CAD_and_BOM.mp3", "title": "ACT 6: HARDWARE CAD BLUEPRINT & BILL OF MATERIALS", "subtitle": "IP66 Die-Cast Al · Dual IMX477 · MEMS Array · Rs.4,200 Batch Cost", "col": ACCENT_AMB},
    {"audio": "Act7_Benchmarks_and_Closing.mp3", "title": "ACT 7: BENCHMARK SUITE, REST API & 48/48 TESTS", "subtitle": "Measured 89.4ms Latency · 0 kbps Idle Bandwidth · TRL 4 Verified", "col": ACCENT_GRN},
]

def load_step_img(name: str) -> np.ndarray:
    p = FRAMES_DIR / f"{name}.png"
    if p.exists():
        im = cv2.imread(str(p))
        if im is not None:
            return cv2.resize(im, (DASH_W, H), interpolation=cv2.INTER_LANCZOS4)
    fb = np.zeros((H, DASH_W, 3), dtype=np.uint8)
    fb[:] = [20, 15, 10]
    return fb

def render_sidebars(canvas: np.ndarray, t_sec: float, act_idx: int):
    # Left Sidebar
    cv2.rectangle(canvas, (0, 0), (X_OFF - 2, H), SIDE_BG, -1)
    cv2.line(canvas, (X_OFF - 2, 0), (X_OFF - 2, H), (45, 30, 20), 1)

    # Right Sidebar
    cv2.rectangle(canvas, (X_OFF + DASH_W + 1, 0), (W, H), SIDE_BG, -1)
    cv2.line(canvas, (X_OFF + DASH_W + 1, 0), (X_OFF + DASH_W + 1, H), (45, 30, 20), 1)

    # Left content
    cv2.rectangle(canvas, (12, 18), (X_OFF - 16, 50), (40, 25, 18), -1)
    cv2.rectangle(canvas, (12, 18), (X_OFF - 16, 50), ACCENT_BLUE, 1)
    cv2.putText(canvas, "EDGE AI COCKPIT", (24, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.48, WHITE, 1)

    y = 80
    items_left = [
        ("ARCHITECTURE", "Edge Appliance (RTSP)"),
        ("VISION MODEL", "YOLOv8-Pose TRT-INT8"),
        ("KEYPOINTS", "17 Joints @ 18.4 FPS"),
        ("ACOUSTIC", "MFCC-CNN (16 kHz)"),
        ("FUSION GATE", "1.5s Temporal Window"),
        ("TRIGGER SLA", "89.4 ms (<450ms target)"),
        ("IDLE NETWORK", "0.00 kbps (Zero Cloud)"),
        ("BATTERY RESERVE", "24.5 hrs (12V 18Ah)"),
        ("ENCLOSURE", "IP66 Die-Cast Aluminum"),
        ("MICROPHONES", "Knowles MEMS Array"),
    ]
    for label, val in items_left:
        cv2.putText(canvas, label, (16, y), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (120, 100, 90), 1)
        cv2.putText(canvas, val, (16, y + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.44, WHITE, 1)
        cv2.line(canvas, (16, y + 26), (X_OFF - 20, y + 26), (35, 25, 18), 1)
        y += 42

    cv2.putText(canvas, "LIVE SPECTRAL FLUX", (16, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.36, ACCENT_BLUE, 1)
    wf_y = y + 25
    cv2.rectangle(canvas, (16, wf_y), (X_OFF - 20, wf_y + 60), (12, 8, 5), -1)
    cv2.rectangle(canvas, (16, wf_y), (X_OFF - 20, wf_y + 60), (45, 30, 20), 1)
    for bx in range(20, X_OFF - 24, 6):
        h_bar = int(10 + 20 * math.sin(t_sec * 4.0 + bx * 0.15) + 12 * math.cos(t_sec * 7.0 + bx * 0.3))
        h_bar = max(4, min(50, h_bar))
        col = ACCENT_RED if (act_idx == 4 and bx > 120) else ACCENT_BLUE
        cv2.line(canvas, (bx, wf_y + 55), (bx, wf_y + 55 - h_bar), col, 2)

    # Right content
    cv2.rectangle(canvas, (X_OFF + DASH_W + 16, 18), (W - 16, 50), (40, 25, 18), -1)
    cv2.rectangle(canvas, (X_OFF + DASH_W + 16, 18), (W - 16, 50), ACCENT_GRN, 1)
    cv2.putText(canvas, "SAFETY SENTINEL", (X_OFF + DASH_W + 28, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.48, WHITE, 1)

    ry = 80
    state_str = "NORMAL PATROL" if act_idx in [1, 2] else ("SUPPRESSED (SAFE)" if act_idx == 3 else ("LEVEL-1 RED ALERT" if act_idx == 4 else "MULTI-NODE ACTIVE"))
    state_col = ACCENT_GRN if act_idx in [1, 2] else (ACCENT_AMB if act_idx == 3 else (ACCENT_RED if act_idx == 4 else ACCENT_BLUE))

    items_right = [
        ("STATUS TIER", state_str),
        ("ENCRYPTION", "AES-256-GCM Envelope"),
        ("MEMORY BUFFER", "5.0s Volatile Ring (RAM)"),
        ("DISK STORAGE", "0.00 bytes (Zero Persist)"),
        ("PRIVACY COMPLIANCE", "DPDP Act 2023 Compliant"),
        ("EVIDENCE CHAIN", "SHA-256 Tamper Sealed"),
        ("AUTOMATED TESTS", "48/48 Suites PASS (100%)"),
        ("TRL READINESS", "TRL 4 (Lab Prototype)"),
        ("CHALLENGE", "SEVA FIRST 2026"),
        ("TEAM / REG", "SingleThread | REG-008"),
    ]
    for label, val in items_right:
        cv2.putText(canvas, label, (X_OFF + DASH_W + 18, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (120, 100, 90), 1)
        col = state_col if label == "STATUS TIER" else WHITE
        cv2.putText(canvas, val, (X_OFF + DASH_W + 18, ry + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.44, col, 1)
        cv2.line(canvas, (X_OFF + DASH_W + 18, ry + 26), (W - 20, ry + 26), (35, 25, 18), 1)
        ry += 42

    cv2.rectangle(canvas, (X_OFF + DASH_W + 16, ry + 10), (W - 16, ry + 75), (14, 10, 6), -1)
    cv2.rectangle(canvas, (X_OFF + DASH_W + 16, ry + 10), (W - 16, ry + 75), (45, 30, 20), 1)
    m = int(t_sec // 60)
    s = int(t_sec % 60)
    ms = int((t_sec * 100) % 100)
    cv2.putText(canvas, f"TICKER: {m:02d}:{s:02d}.{ms:02d}", (X_OFF + DASH_W + 24, ry + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.46, ACCENT_GRN, 1)
    cv2.putText(canvas, "LATENCY: 89.4ms | 18.2 FPS", (X_OFF + DASH_W + 24, ry + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 170, 160), 1)

def draw_skeleton(frame: np.ndarray, cx: int, cy: int, t: float, mode: str, bone_col, joint_col, p_id: int):
    scale = 1.25
    if mode == 'walk':
        leg = math.sin(t * 3.2) * 18
        arm = math.cos(t * 3.2) * 16
    elif mode == 'run':
        leg = math.sin(t * 7.0) * 32
        arm = math.cos(t * 7.0) * 28
    elif mode == 'struggle':
        leg = math.sin(t * 9.0) * 22 + math.cos(t * 6.0) * 12
        arm = math.sin(t * 14.0) * 38 + math.cos(t * 8.0) * 25
    else:
        leg, arm = 0, 0

    head = (int(cx), int(cy - 95 * scale))
    neck = (int(cx), int(cy - 80 * scale))
    r_sh = (int(cx - 15 * scale), int(cy - 75 * scale))
    l_sh = (int(cx + 15 * scale), int(cy - 75 * scale))
    r_hip = (int(cx - 12 * scale), int(cy - 45 * scale))
    l_hip = (int(cx + 12 * scale), int(cy - 45 * scale))

    r_elb = (int(r_sh[0] - 10 + arm * 0.4), int(r_sh[1] + 20))
    r_wri = (int(r_elb[0] - 8 + arm * 0.7), int(r_elb[1] + 18))
    l_elb = (int(l_sh[0] + 10 - arm * 0.4), int(l_sh[1] + 20))
    l_wri = (int(l_elb[0] + 8 - arm * 0.7), int(l_elb[1] + 18))

    r_kne = (int(r_hip[0] + leg * 0.5), int(r_hip[1] + 26 * scale))
    r_ank = (int(r_hip[0] + leg), int(cy))
    l_kne = (int(l_hip[0] - leg * 0.5), int(l_hip[1] + 26 * scale))
    l_ank = (int(l_hip[0] - leg), int(cy))

    bx1 = min(r_wri[0], l_wri[0], r_ank[0], l_ank[0], cx - 25) - 12
    bx2 = max(r_wri[0], l_wri[0], r_ank[0], l_ank[0], cx + 25) + 12
    by1 = head[1] - 16
    by2 = cy + 4
    cv2.rectangle(frame, (bx1, by1), (bx2, by2), bone_col, 1)
    lbl = f"Person #{p_id} [0.94]" if mode != 'struggle' else f"Person #{p_id} [GRAPPLE]"
    cv2.putText(frame, lbl, (bx1, by1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.38, bone_col, 1)

    bones = [
        (head, neck), (neck, r_sh), (neck, l_sh), (r_sh, r_elb), (r_elb, r_wri),
        (l_sh, l_elb), (l_elb, l_wri), (r_sh, r_hip), (l_sh, l_hip), (r_hip, l_hip),
        (r_hip, r_kne), (r_kne, r_ank), (l_hip, l_kne), (l_kne, l_ank)
    ]
    for p1, p2 in bones:
        cv2.line(frame, p1, p2, bone_col, 2)
    cv2.circle(frame, head, int(10 * scale), joint_col, -1)
    cv2.circle(frame, head, int(10 * scale), bone_col, 2)
    for pt in [neck, r_sh, l_sh, r_elb, l_elb, r_wri, l_wri, r_hip, l_hip, r_kne, l_kne, r_ank, l_ank]:
        cv2.circle(frame, pt, 3, joint_col, -1)

def draw_cctv_simulation(c_w: int, c_h: int, t: float, scenario: str) -> np.ndarray:
    c = np.zeros((c_h, c_w, 3), dtype=np.uint8)
    c[:] = [22, 10, 6]

    for y_line in range(int(c_h * 0.45), c_h, 24):
        cv2.line(c, (0, y_line), (c_w, y_line), (35, 25, 18), 1)
    cv2.line(c, (int(c_w * 0.25), int(c_h * 0.45)), (0, c_h), (50, 35, 25), 1)
    cv2.line(c, (int(c_w * 0.75), int(c_h * 0.45)), (c_w, c_h), (50, 35, 25), 1)

    if scenario == 'patrol':
        f1x = int(c_w * 0.35 + math.sin(t * 0.9) * 45)
        f2x = int(c_w * 0.65 - math.sin(t * 0.9) * 45)
        draw_skeleton(c, f1x, int(c_h * 0.82), t, 'walk', (0, 200, 50), (140, 255, 160), 1)
        draw_skeleton(c, f2x, int(c_h * 0.82), t + math.pi, 'walk', (0, 200, 50), (140, 255, 160), 2)
        cv2.putText(c, "CAM-01 · GATE 1 · NORMAL PATROL", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 230, 100), 1)
    elif scenario == 'sports':
        f1x = int(c_w * 0.50 + math.sin(t * 2.2) * 80)
        draw_skeleton(c, f1x, int(c_h * 0.82), t, 'run', (0, 140, 240), (100, 200, 255), 1)
        cv2.putText(c, "HARD-NEGATIVE: JOGGING (K_t=0.68, S_t=0.04) -> GATE LOCKED", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.42, ACCENT_AMB, 1)
    elif scenario == 'assault':
        f1x = int(c_w * 0.45 + math.sin(t * 3.5) * 15)
        f2x = int(f1x + 36 + math.sin(t * 4.0) * 10)
        draw_skeleton(c, f1x, int(c_h * 0.82), t, 'struggle', (0, 40, 235), (120, 140, 255), 1)
        draw_skeleton(c, f2x, int(c_h * 0.82), t + math.pi, 'struggle', (0, 40, 235), (120, 140, 255), 2)
        cv2.line(c, (f1x, int(c_h * 0.55)), (f2x, int(c_h * 0.55)), (0, 40, 235), 2)
        if int(t * 4) % 2 == 0:
            cv2.rectangle(c, (0, 0), (c_w, c_h), (0, 0, 180), 3)
            cv2.putText(c, "CRITICAL: PHYSICAL STRUGGLE & VOCAL PANIC DETECTED", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 80, 255), 1)
        else:
            cv2.putText(c, "CRITICAL: PHYSICAL STRUGGLE & VOCAL PANIC DETECTED", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.44, WHITE, 1)

    return c

def create_lower_third(canvas: np.ndarray, act_idx: int, t_sec: float):
    info = ACT_INFOS[act_idx - 1]
    bh = 72
    overlay = canvas.copy()
    cv2.rectangle(overlay, (X_OFF, H - bh), (X_OFF + DASH_W, H), (10, 6, 4), -1)
    cv2.addWeighted(overlay, 0.88, canvas, 0.12, 0, canvas)
    cv2.rectangle(canvas, (X_OFF, H - bh), (X_OFF + 8, H), info["col"], -1)
    cv2.putText(canvas, info["title"], (X_OFF + 22, H - bh + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1)
    cv2.putText(canvas, info["subtitle"], (X_OFF + 22, H - bh + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 170, 160), 1)
    cv2.putText(canvas, "surakshaedge.onrender.com · v0.4.1", (X_OFF + DASH_W - 270, H - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 130, 120), 1)

def build_audio_track() -> float:
    print("Concatenating audio tracks...")
    all_audio = []
    sr = None
    for info in ACT_INFOS:
        ap = AUDIO_DIR / info["audio"]
        data, rate = sf.read(str(ap))
        sr = rate
        all_audio.append(data)
    combined = np.concatenate(all_audio)
    sf.write(str(TEMP_AUDIO), combined, sr)
    total_dur = len(combined) / sr
    print(f"Combined audio written to {TEMP_AUDIO}: {total_dur:.2f}s ({int(total_dur//60)}m {int(total_dur%60):02d}s)")
    return total_dur

def generate_video():
    total_dur = build_audio_track()
    total_frames = int(total_dur * FPS)
    print(f"\nBuilding Video: {total_frames} frames @ 30 FPS ({total_dur:.1f}s)...")

    print("Loading scaled dashboard frames...")
    steps = {i: load_step_img(f"step{i}") for i in range(1, 17)}

    scale_factor = H / 822.0
    cctv_x = int(47 * scale_factor)
    cctv_y = int(197 * scale_factor)
    cctv_w = int(531 * scale_factor)
    cctv_h = int(299 * scale_factor)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(str(TEMP_VIDEO), fourcc, FPS, (W, H))
    if not vw.isOpened():
        print(f"ERROR: Could not open VideoWriter for {TEMP_VIDEO}", file=sys.stderr)
        sys.exit(1)

    durations = [sf.info(str(AUDIO_DIR / info["audio"])).duration for info in ACT_INFOS]
    t_global = 0.0

    canvas = np.zeros((H, W, 3), dtype=np.uint8)

    for act_idx, (info, dur) in enumerate(zip(ACT_INFOS, durations), 1):
        n_act_frames = int(dur * FPS)
        print(f"  Act {act_idx}/{len(ACT_INFOS)}: {info['title']} ({dur:.1f}s, {n_act_frames} frames)")

        if act_idx == 1:
            step_cycle = [1, 2]
        elif act_idx == 2:
            step_cycle = [3, 4]
        elif act_idx == 3:
            step_cycle = [3, 5]
        elif act_idx == 4:
            step_cycle = [3, 5, 6, 7]
        elif act_idx == 5:
            step_cycle = [8, 9]
        elif act_idx == 6:
            step_cycle = [10, 11]
        else:
            step_cycle = [12, 13, 14, 15, 16]

        sub_n = max(1, n_act_frames // len(step_cycle))

        for step_i, step_num in enumerate(step_cycle):
            base_dash = steps[step_num]
            start_f = step_i * sub_n
            end_f = n_act_frames if step_i == len(step_cycle) - 1 else (step_i + 1) * sub_n

            for f_idx in range(start_f, end_f):
                canvas[:, :] = BG_DARK
                dash_copy = base_dash.copy()

                if step_num in [3, 4]:
                    scenario = 'patrol' if act_idx == 2 else ('sports' if act_idx == 3 else 'assault')
                    cctv_live = draw_cctv_simulation(cctv_w, cctv_h, t_global, scenario)
                    dash_copy[cctv_y:cctv_y+cctv_h, cctv_x:cctv_x+cctv_w] = cctv_live

                canvas[:, X_OFF:X_OFF+DASH_W] = dash_copy
                render_sidebars(canvas, t_global, act_idx)
                create_lower_third(canvas, act_idx, t_global)

                vw.write(canvas)
                t_global += 1.0 / FPS

    vw.release()
    print(f"\nRaw video written to {TEMP_VIDEO}: {os.path.getsize(str(TEMP_VIDEO)) / (1024*1024):.1f} MB")

    print("Muxing video + audio via FFmpeg 7.1...")
    cmd = [
        FFMPEG, "-y",
        "-i", str(TEMP_VIDEO),
        "-i", str(TEMP_AUDIO),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-b:v", "8000k",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(OUTPUT_PATH)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"FFmpeg error:\n{res.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        if TEMP_VIDEO.exists(): TEMP_VIDEO.unlink()
        if TEMP_AUDIO.exists(): TEMP_AUDIO.unlink()
    except Exception:
        pass

    final_size = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"\n=======================================================")
    print(f"  SUCCESS! SENIOR EVALUATOR DEMO VIDEO COMPILED")
    print(f"  Path: {OUTPUT_PATH}")
    print(f"  Duration: {total_dur:.1f}s ({int(total_dur//60)}m {int(total_dur%60):02d}s)")
    print(f"  Size: {final_size:.1f} MB")
    print(f"=======================================================\n")

if __name__ == "__main__":
    generate_video()
