"""
SurakshaEdge — Synthetic Demo Clip Generator
Generates a 10-second MP4 showing two 'people' (rectangles) colliding in a struggle,
with animated K_t score overlay. Used as a visual aid in demo recordings.

Usage:
    python scripts/gen_demo_clip.py
    # Outputs: data/clips/DEMO_assault_T01.mp4
"""
from __future__ import annotations

import os
import sys

import numpy as np

try:
    import cv2
except ImportError:
    print("ERROR: opencv-python required. pip install opencv-python", file=sys.stderr)
    sys.exit(1)

W, H = 640, 480
FPS = 25
DURATION_S = 10
TOTAL_FRAMES = FPS * DURATION_S

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "clips", "DEMO_assault_T01.mp4")


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def draw_skeleton_person(frame: np.ndarray, cx: int, cy: int, color, flail: float = 0.0):
    """Draw a simple stick figure person at (cx, cy) with flailing arms."""
    # Body
    cv2.line(frame, (cx, cy - 30), (cx, cy + 30), color, 3)
    # Head
    cv2.circle(frame, (cx, cy - 40), 12, color, -1)
    # Arms — flail is 0..1 for arm angle variance
    arm_angle = int(flail * 60)
    lw = (cx - 35 + arm_angle, cy - 10 + arm_angle)
    rw = (cx + 35 - arm_angle, cy - 10 - arm_angle)
    cv2.line(frame, (cx, cy - 15), lw, color, 3)
    cv2.line(frame, (cx, cy - 15), rw, color, 3)
    # Legs
    cv2.line(frame, (cx, cy + 30), (cx - 15 + int(flail * 10), cy + 65), color, 3)
    cv2.line(frame, (cx, cy + 30), (cx + 15 - int(flail * 10), cy + 65), color, 3)


def make_gradient_bg(frame_idx: int) -> np.ndarray:
    """Dark gradient background that subtly shifts."""
    img = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        v = int(20 + (y / H) * 20)
        img[y, :] = [v, v + 5, v + 2]
    return img


def main():
    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(os.path.abspath(OUTPUT_PATH), fourcc, FPS, (W, H))
    if not out.isOpened():
        print(f"ERROR: Could not open VideoWriter for {OUTPUT_PATH}", file=sys.stderr)
        sys.exit(1)

    for frame_idx in range(TOTAL_FRAMES):
        t = frame_idx / TOTAL_FRAMES  # 0.0 → 1.0
        t_s = frame_idx / FPS

        img = make_gradient_bg(frame_idx)

        # Simulate K_t rising: 0.20 → 0.78 over first 8s, then holds
        if t_s < 2.0:
            K_t = lerp(0.20, 0.45, t_s / 2.0)
        elif t_s < 5.0:
            K_t = lerp(0.45, 0.78, (t_s - 2.0) / 3.0)
        else:
            K_t = 0.78 + 0.03 * np.sin(t_s * 8)

        # S_t rises from 3.5s onwards
        if t_s < 3.5:
            S_t = 0.05
        elif t_s < 5.0:
            S_t = lerp(0.05, 0.85, (t_s - 3.5) / 1.5)
        else:
            S_t = 0.85 + 0.05 * np.sin(t_s * 6)

        K_t = float(np.clip(K_t, 0, 1))
        S_t = float(np.clip(S_t, 0, 1))

        # Determine gate state
        if t_s >= 4.0:
            tier = "ALERT"
            tier_color = (0, 0, 220)
        elif K_t >= 0.62:
            tier = "ADVISORY"
            tier_color = (0, 120, 220)
        else:
            tier = "NORMAL"
            tier_color = (0, 180, 0)

        # Person A: left side, moving right to close gap
        gap = max(0, 200 - int(t_s * 25))
        ax = max(W // 2 - gap, W // 2 - 60)
        ay = H // 2 - 20

        # Person B: right side, moving left
        bx = min(W // 2 + gap, W // 2 + 60)
        by = H // 2 - 20

        # Flailing intensity
        flail = min(1.0, K_t * 1.3)
        flail_a = flail * (1 + 0.2 * np.sin(frame_idx * 0.8))
        flail_b = flail * (1 + 0.2 * np.sin(frame_idx * 0.9 + 1.0))

        # Draw persons
        draw_skeleton_person(img, ax, ay, (60, 160, 255), flail_a)
        draw_skeleton_person(img, bx, by, (60, 255, 160), flail_b)

        # --- HUD Overlay ---
        # Score bars background
        cv2.rectangle(img, (10, 10), (310, 110), (20, 20, 30), -1)
        cv2.rectangle(img, (10, 10), (310, 110), (60, 60, 80), 1)

        # K_t bar
        kbar_len = int(K_t * 240)
        kbar_color = (0, 100, 220) if K_t < 0.6 else (0, 165, 255) if K_t < 0.75 else (0, 50, 220)
        cv2.rectangle(img, (60, 25), (60 + kbar_len, 48), kbar_color, -1)
        cv2.putText(img, f"K_t  {K_t:.2f}", (15, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        # S_t bar
        sbar_len = int(S_t * 240)
        sbar_color = (0, 200, 60) if S_t < 0.6 else (0, 200, 180) if S_t < 0.75 else (0, 80, 220)
        cv2.rectangle(img, (60, 60), (60 + sbar_len, 83), sbar_color, -1)
        cv2.putText(img, f"S_t  {S_t:.2f}", (15, 79), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        # Tier badge
        cv2.rectangle(img, (60, 90), (200, 108), tier_color, -1)
        cv2.putText(img, tier, (65, 104), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Title
        cv2.putText(img, "SurakshaEdge  |  SEVA FIRST 2026",
                    (10, H - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 150), 1)

        # Timestamp
        cv2.putText(img, f"t = {t_s:.1f}s",
                    (W - 90, H - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 150), 1)

        # ALERT banner flash
        if tier == "ALERT":
            flash = int(abs(np.sin(frame_idx * 0.5)) * 80)
            cv2.rectangle(img, (0, 0), (W, H), (0, 0, flash + 80), 2)
            cv2.putText(img, "⚡ DUAL-SIGNAL FUSION ALERT ⚡",
                        (W // 2 - 165, H // 2 - 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 50, 230), 2)

        out.write(img)
        if frame_idx % 50 == 0:
            print(f"  Frame {frame_idx}/{TOTAL_FRAMES}  K_t={K_t:.2f}  S_t={S_t:.2f}  tier={tier}")

    out.release()
    size = os.path.getsize(os.path.abspath(OUTPUT_PATH))
    print(f"\nGenerated: {os.path.abspath(OUTPUT_PATH)} ({size / 1024:.0f} KB)")
    if size < 100_000:
        print("WARNING: file seems small — check codec support", file=sys.stderr)
    else:
        print("OK — clip ready for demo recording")


if __name__ == "__main__":
    main()
