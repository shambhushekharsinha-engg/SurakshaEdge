"""
SurakshaEdge — 4:50 Demo Video Generator
Assembles browser screenshots + AI voiceover into a professional MP4.
Pipeline:
  1. Load 16 browser screenshots (video_frames/step1..16.png)
  2. Load 7 voiceover MP3s (data/audio/voiceover/Act*.mp3)
  3. Assign screenshots to time segments matching voiceover acts
  4. Add title cards, lower-third labels, and transition overlays
  5. Output: data/SEVA_FIRST_SurakshaEdge_Demo.mp4

Requirements: moviepy, Pillow, edge-tts
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parents[1]
FRAMES_DIR   = Path(r"C:\Users\shamb\.gemini\antigravity\brain\3dd2ba4e-ad18-4375-80c1-81e1f903c5bd\video_frames")
AUDIO_DIR    = ROOT / "data" / "audio" / "voiceover"
OUTPUT_PATH  = ROOT / "data" / "SEVA_FIRST_SurakshaEdge_Demo.mp4"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Video constants ───────────────────────────────────────────────────────────
W, H  = 1920, 1080
FPS   = 30
TOTAL_TARGET = 290  # 4:50 in seconds

# ── Color palette (matches SurakshaEdge dark theme) ─────────────────────────
BG_COLOR      = (15, 23, 42)       # #0f172a
ACCENT_RED    = (239, 68, 68)      # #ef4444
ACCENT_AMBER  = (251, 146, 60)     # #f97316
ACCENT_BLUE   = (99, 160, 246)     # #63a0f6
WHITE         = (255, 255, 255)
SUBTITLE_BG   = (0, 0, 0, 180)    # semi-transparent

# ── Act → screenshot mapping ────────────────────────────────────────────────
# Each act: (title, subtitle, screen_steps, audio_file)
ACTS = [
    {
        "title":    "The Crisis — Passive Surveillance Fails",
        "subtitle": "NCRB: 4,00,000+ crimes against women annually · 95% of CCTV is purely passive",
        "steps":    [1, 2],
        "audio":    "Act1_The_Reality_and_The_Gap.mp3",
        "color":    ACCENT_RED,
    },
    {
        "title":    "Live Edge AI — Skeleton Inspector",
        "subtitle": "YOLOv8-Pose · 18 FPS on CPU · 17 keypoints · MFCC-CNN Audio Classifier",
        "steps":    [3, 4],
        "audio":    "Act2_Architecture_and_Skeleton_Inspector.mp3",
        "color":    ACCENT_BLUE,
    },
    {
        "title":    "Hard-Negative Suppression — Zero False Alarms",
        "subtitle": "Dual-Signal Fusion Gate: grapple + vocal distress must coincide within 1.5s",
        "steps":    [5, 6],
        "audio":    "Act3_Hard_Negative_Suppression.mp3",
        "color":    ACCENT_AMBER,
    },
    {
        "title":    "Live Assault Alert — 89ms End-to-End",
        "subtitle": "AES-256-GCM encrypted event · Zero disk persistence · RAM ring buffer only",
        "steps":    [6, 7, 8],
        "audio":    "Act4_Assault_Alert_and_Encrypted_Replay.mp3",
        "color":    ACCENT_RED,
    },
    {
        "title":    "Multi-Node Coordination Across Campus",
        "subtitle": "Autonomous per-node operation · No single-point cloud failure",
        "steps":    [9],
        "audio":    "Act5_Multi_Node_and_Telemetry_Export.mp3",
        "color":    ACCENT_BLUE,
    },
    {
        "title":    "Hardware Blueprint — ₹4,200/node at Scale",
        "subtitle": "IP66 die-cast Al · NVIDIA Jetson Orin Nano · Knowles MEMS array · 5G ready",
        "steps":    [10, 11],
        "audio":    "Act6_Hardware_CAD_and_BOM.mp3",
        "color":    ACCENT_AMBER,
    },
    {
        "title":    "Benchmarks · API Docs · 48/48 Tests Passing",
        "subtitle": "Trigger latency 89.4ms · 0 kbps idle · 24.5h battery · TRL 4 ✓",
        "steps":    [12, 13, 14, 15, 16],
        "audio":    "Act7_Benchmarks_and_Closing.mp3",
        "color":    ACCENT_BLUE,
    },
]


def load_font(size: int):
    """Try system fonts, fall back to default."""
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def make_title_card(title: str, subtitle: str, duration_s: float, fps: int, color) -> list:
    """Generate frames for a 2.5-second animated title card."""
    frames = []
    n = int(duration_s * fps)
    font_title = load_font(52)
    font_sub   = load_font(28)
    font_badge = load_font(20)

    for i in range(n):
        t = i / n
        alpha = min(1.0, t * 4) if t < 0.5 else min(1.0, (1 - t) * 4)
        img = Image.new("RGB", (W, H), BG_COLOR)
        d = ImageDraw.Draw(img)

        # Accent line
        bar_w = int(W * min(1.0, t * 3))
        d.rectangle([(0, H//2 - 4), (bar_w, H//2 + 4)], fill=color)

        # Title
        d.text((W//2, H//2 - 50), title, font=font_title, fill=WHITE,
               anchor="mm", align="center")
        # Subtitle
        d.text((W//2, H//2 + 30), subtitle, font=font_sub,
               fill=(148, 163, 184), anchor="mm", align="center")
        # Branding
        d.text((W - 20, H - 20), "SurakshaEdge · SEVA FIRST 2026 · REG-008-OP-024",
               font=font_badge, fill=(71, 85, 105), anchor="rs")

        frames.append(np.array(img))
    return frames


def overlay_lower_third(img_array: np.ndarray, subtitle: str, color) -> np.ndarray:
    """Burn a lower-third label onto a frame."""
    img = Image.fromarray(img_array).resize((W, H), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    font = load_font(26)
    badge_font = load_font(18)

    # Lower third bar
    bar_h = 60
    overlay = Image.new("RGBA", (W, bar_h), (0, 0, 0, 180))
    img.paste(Image.fromarray(np.array(overlay)[:,:,:3]), (0, H - bar_h),
              mask=Image.fromarray(np.array(overlay)[:,:,3]))

    # Accent strip
    d.rectangle([(0, H - bar_h), (6, H)], fill=color)

    # Text
    d.text((20, H - bar_h + 8), subtitle, font=font, fill=WHITE)
    d.text((W - 20, H - 15), "surakshaedge.onrender.com",
           font=badge_font, fill=(100, 116, 139), anchor="rs")

    return np.array(img.convert("RGB"))


def screenshot_to_frames(step_num: int, duration_s: float, fps: int,
                          subtitle: str, color) -> list:
    """Load a screenshot and repeat it for `duration_s` seconds with lower-third."""
    path = FRAMES_DIR / f"step{step_num}.png"
    if not path.exists():
        # Fallback: dark placeholder with text
        img = Image.new("RGB", (W, H), BG_COLOR)
        d = ImageDraw.Draw(img)
        d.text((W//2, H//2), f"[Step {step_num}]", font=load_font(40),
               fill=(71, 85, 105), anchor="mm")
        base = np.array(img)
    else:
        base = np.array(Image.open(path).convert("RGB"))

    frame = overlay_lower_third(base, subtitle, color)
    n = max(1, int(duration_s * fps))
    return [frame] * n


def get_audio_duration(filename: str) -> float:
    path = AUDIO_DIR / filename
    if not path.exists():
        return 30.0
    try:
        info = sf.info(str(path))
        return info.duration
    except Exception:
        return 30.0


def build_video():
    from moviepy import AudioFileClip, ImageSequenceClip, concatenate_audioclips

    print(f"Building SurakshaEdge Demo Video → {OUTPUT_PATH}")
    print(f"Target: {TOTAL_TARGET}s (4:50)")

    all_frames = []
    all_audio_clips = []
    t_cursor = 0.0

    # ── Intro title card (3s) ────────────────────────────────────────────────
    intro_frames = make_title_card(
        "SurakshaEdge",
        "Edge AI Assault Detection · SEVA FIRST Rashtriya Youth Innovation Challenge 2026",
        3.0, FPS, ACCENT_BLUE
    )
    all_frames.extend(intro_frames)
    t_cursor += 3.0

    # ── Team card (2s) ───────────────────────────────────────────────────────
    team_frames = make_title_card(
        "Team SingleThread",
        "GNIOT, Greater Noida  ·  REG-008-OP-024  ·  Track II – Women & Child Safety",
        2.0, FPS, ACCENT_AMBER
    )
    all_frames.extend(team_frames)
    t_cursor += 2.0

    # ── Acts ─────────────────────────────────────────────────────────────────
    for act_idx, act in enumerate(ACTS, 1):
        audio_duration = get_audio_duration(act["audio"])
        print(f"\n  Act {act_idx}: {act['title']} ({audio_duration:.1f}s)")

        # Act title card (2s)
        title_frames = make_title_card(
            f"Act {act_idx}: {act['title']}", act["subtitle"],
            2.0, FPS, act["color"]
        )
        all_frames.extend(title_frames)

        # Distribute screenshots evenly over audio duration
        steps = act["steps"]
        per_step = max(2.0, (audio_duration) / len(steps))

        for step_num in steps:
            step_frames = screenshot_to_frames(
                step_num, per_step, FPS,
                act["subtitle"], act["color"]
            )
            all_frames.extend(step_frames)
            print(f"    Step {step_num}: {per_step:.1f}s × {FPS}fps = {len(step_frames)} frames")

        # Audio clip
        audio_path = AUDIO_DIR / act["audio"]
        if audio_path.exists():
            clip = AudioFileClip(str(audio_path))
            all_audio_clips.append(clip)
        else:
            print(f"    WARNING: Audio not found: {audio_path}")

        t_cursor += 2.0 + audio_duration

    # ── Outro (3s) ───────────────────────────────────────────────────────────
    outro_frames = make_title_card(
        "SurakshaEdge — Making India Safer",
        "48/48 Tests · 89ms Latency · Zero Disk Persistence · TRL 4 ✓ · surakshaedge.onrender.com",
        3.0, FPS, ACCENT_BLUE
    )
    all_frames.extend(outro_frames)
    t_cursor += 3.0

    total_frames = len(all_frames)
    actual_duration = total_frames / FPS
    print(f"\nTotal frames: {total_frames} → {actual_duration:.1f}s ({int(actual_duration//60)}m{int(actual_duration%60):02d}s)")

    # ── Write video ───────────────────────────────────────────────────────────
    print("Encoding video...")
    video_clip = ImageSequenceClip(all_frames, fps=FPS)

    if all_audio_clips:
        from moviepy import concatenate_audioclips
        combined_audio = concatenate_audioclips(all_audio_clips)
        # Trim or pad audio to match video length
        if combined_audio.duration > video_clip.duration:
            combined_audio = combined_audio.subclipped(0, video_clip.duration)
        video_clip = video_clip.with_audio(combined_audio)

    video_clip.write_videofile(
        str(OUTPUT_PATH),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="8000k",
        preset="medium",
        logger="bar",
    )

    size_mb = OUTPUT_PATH.stat().st_size / 1_048_576
    print(f"\n✅ VIDEO READY: {OUTPUT_PATH}")
    print(f"   Duration: {actual_duration:.1f}s | Size: {size_mb:.1f} MB")


if __name__ == "__main__":
    build_video()
