"""
SurakshaEdge — v2 Demo Video Builder
Uses video_frames2/ for the re-captured live screenshots.
Identical to build_demo_video.py but reads from video_frames2.
"""
from __future__ import annotations
import os, sys
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import soundfile as sf

ROOT         = Path('C:/SurakshaEdge/surakshaedge')
FRAMES_DIR   = Path(r"C:\Users\shamb\.gemini\antigravity\brain\3dd2ba4e-ad18-4375-80c1-81e1f903c5bd\video_frames2")
AUDIO_DIR    = ROOT / "data" / "audio" / "voiceover"
OUTPUT_PATH  = ROOT / "data" / "SEVA_FIRST_SurakshaEdge_FINAL.mp4"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

W, H  = 1920, 1080
FPS   = 30

BG_COLOR     = (15, 23, 42)
ACCENT_RED   = (239, 68, 68)
ACCENT_AMBER = (251, 146, 60)
ACCENT_BLUE  = (99, 160, 246)
WHITE        = (255, 255, 255)

ACTS = [
    {"title": "The Crisis — Passive Surveillance Fails",
     "subtitle": "NCRB: 4,00,000+ crimes against women annually · 95% of CCTV is purely passive",
     "steps": [1, 2], "audio": "Act1_The_Reality_and_The_Gap.mp3", "color": ACCENT_RED},
    {"title": "Live Edge AI — Skeleton Inspector",
     "subtitle": "YOLOv8-Pose · 18 FPS on CPU · 17 keypoints · MFCC-CNN Audio Classifier",
     "steps": [3, 4], "audio": "Act2_Architecture_and_Skeleton_Inspector.mp3", "color": ACCENT_BLUE},
    {"title": "Hard-Negative Suppression — Zero False Alarms",
     "subtitle": "Dual-Signal Fusion Gate: grapple + vocal distress must coincide within 1.5s",
     "steps": [5, 6], "audio": "Act3_Hard_Negative_Suppression.mp3", "color": ACCENT_AMBER},
    {"title": "Live Assault Alert — 89ms End-to-End",
     "subtitle": "AES-256-GCM encrypted event · Zero disk persistence · RAM ring buffer only",
     "steps": [6, 7, 8], "audio": "Act4_Assault_Alert_and_Encrypted_Replay.mp3", "color": ACCENT_RED},
    {"title": "Multi-Node Coordination Across Campus",
     "subtitle": "Autonomous per-node operation · No single-point cloud failure",
     "steps": [9], "audio": "Act5_Multi_Node_and_Telemetry_Export.mp3", "color": ACCENT_BLUE},
    {"title": "Hardware Blueprint — Rs.4,200/node at Scale",
     "subtitle": "IP66 die-cast Al · NVIDIA Jetson Orin Nano · Knowles MEMS array · 5G ready",
     "steps": [10, 11], "audio": "Act6_Hardware_CAD_and_BOM.mp3", "color": ACCENT_AMBER},
    {"title": "Benchmarks · API · 48/48 Tests Passing",
     "subtitle": "Trigger latency 89.4ms · 0 kbps idle · 24.5h battery · TRL 4",
     "steps": [12, 13, 14, 15, 16], "audio": "Act7_Benchmarks_and_Closing.mp3", "color": ACCENT_BLUE},
]


def load_font(size):
    for f in ["C:/Windows/Fonts/segoeui.ttf","C:/Windows/Fonts/arial.ttf","C:/Windows/Fonts/calibri.ttf"]:
        if os.path.exists(f):
            try: return ImageFont.truetype(f, size)
            except: pass
    return ImageFont.load_default()


def make_title_card(title, subtitle, duration_s, fps, color):
    frames, n = [], int(duration_s * fps)
    ft, fs, fb = load_font(52), load_font(28), load_font(20)
    for i in range(n):
        t = i / n
        img = Image.new("RGB", (W, H), BG_COLOR)
        d = ImageDraw.Draw(img)
        bar_w = int(W * min(1.0, t * 3))
        d.rectangle([(0, H//2 - 4), (bar_w, H//2 + 4)], fill=color)
        d.text((W//2, H//2 - 50), title, font=ft, fill=WHITE, anchor="mm")
        d.text((W//2, H//2 + 30), subtitle, font=fs, fill=(148,163,184), anchor="mm")
        d.text((W-20, H-20), "SurakshaEdge · SEVA FIRST 2026 · REG-008-OP-024", font=fb, fill=(71,85,105), anchor="rs")
        frames.append(np.array(img))
    return frames


def overlay_lower_third(img_array, subtitle, color):
    img = Image.fromarray(img_array).resize((W, H), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    # Semi-transparent lower bar
    bar = Image.new("RGBA", (W, 65), (0, 0, 0, 200))
    img.paste(Image.new("RGB",(W,65),(0,0,0)), (0, H-65), mask=bar.split()[3])
    d = ImageDraw.Draw(img)
    d.rectangle([(0, H-65), (8, H)], fill=color)
    d.text((22, H-55), subtitle, font=load_font(26), fill=WHITE)
    d.text((W-20, H-18), "surakshaedge.onrender.com · v0.4.1", font=load_font(18), fill=(100,116,139), anchor="rs")
    return np.array(img.convert("RGB"))


def screenshot_frames(step_num, duration_s, fps, subtitle, color):
    path = FRAMES_DIR / f"step{step_num}.png"
    if not path.exists():
        img = Image.new("RGB", (W, H), BG_COLOR)
        d = ImageDraw.Draw(img)
        d.text((W//2, H//2), f"[Capturing step {step_num}...]", font=load_font(40), fill=(71,85,105), anchor="mm")
        base = np.array(img)
    else:
        base = np.array(Image.open(path).convert("RGB"))
    frame = overlay_lower_third(base, subtitle, color)
    n = max(1, int(duration_s * fps))
    return [frame] * n


def get_audio_dur(filename):
    p = AUDIO_DIR / filename
    return sf.info(str(p)).duration if p.exists() else 30.0


def build():
    from moviepy import ImageSequenceClip, AudioFileClip, concatenate_audioclips
    print(f"Building FINAL video -> {OUTPUT_PATH}")

    all_frames, audio_clips = [], []

    # Intro
    all_frames.extend(make_title_card("SurakshaEdge", "Edge AI Assault Detection · SEVA FIRST Rashtriya Youth Innovation Challenge 2026", 3.0, FPS, ACCENT_BLUE))
    all_frames.extend(make_title_card("Team SingleThread", "GNIOT, Greater Noida  ·  REG-008-OP-024  ·  Track II – Women & Child Safety", 2.0, FPS, ACCENT_AMBER))

    for i, act in enumerate(ACTS, 1):
        dur = get_audio_dur(act["audio"])
        print(f"  Act {i}: {act['title']} ({dur:.1f}s, {len(act['steps'])} screens)")
        all_frames.extend(make_title_card(f"Act {i}: {act['title']}", act["subtitle"], 1.5, FPS, act["color"]))
        per = max(2.0, dur / len(act["steps"]))
        for s in act["steps"]:
            all_frames.extend(screenshot_frames(s, per, FPS, act["subtitle"], act["color"]))
        p = AUDIO_DIR / act["audio"]
        if p.exists(): audio_clips.append(AudioFileClip(str(p)))

    # Outro
    all_frames.extend(make_title_card("SurakshaEdge — Making India Safer", "48/48 Tests · 89ms Latency · Zero Disk Persistence · TRL 4  ·  surakshaedge.onrender.com", 3.0, FPS, ACCENT_BLUE))

    total_s = len(all_frames) / FPS
    print(f"\nTotal: {len(all_frames)} frames = {total_s:.1f}s ({int(total_s//60)}m{int(total_s%60):02d}s)")

    video = ImageSequenceClip(all_frames, fps=FPS)
    if audio_clips:
        audio = concatenate_audioclips(audio_clips)
        if audio.duration > video.duration:
            audio = audio.subclipped(0, video.duration)
        video = video.with_audio(audio)

    # Trim to fit under 5:00; cap at audio duration to avoid ValueError
    target = min(290.0, video.duration)
    if video.audio:
        target = min(target, video.audio.duration)
    if video.duration > target:
        video = video.subclipped(0, target)
        print(f"Trimmed to {target:.1f}s ({int(target//60)}m{int(target%60):02d}s)")

    video.write_videofile(str(OUTPUT_PATH), fps=FPS, codec="libx264", audio_codec="aac", bitrate="8000k", preset="medium", logger="bar")
    size_mb = OUTPUT_PATH.stat().st_size / 1_048_576
    print(f"\nFINAL VIDEO: {OUTPUT_PATH} | {video.duration:.1f}s | {size_mb:.1f} MB")


if __name__ == "__main__":
    build()
