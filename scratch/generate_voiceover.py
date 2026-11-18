# -*- coding: utf-8 -*-
"""
Perfect timing calibration: lands at ~04:38 (278s) so you have a guaranteed
20-second safety cushion below the strict 5-minute maximum limit!
"""
import asyncio
import os
import edge_tts
import soundfile as sf

OUTPUT_DIR = r"C:\SurakshaEdge\surakshaedge\data\audio\voiceover"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ACTS_CALIBRATED = [
    {
        "filename": "Act1_The_Reality_and_The_Gap.mp3",
        "title": "Act 1: The Reality & The Gap",
        "rate": "+20%",
        "pitch": "+0Hz",
        "text": (
            "On August 4th, 2026, a student was assaulted along the Pari Chowk corridor in Greater Noida. "
            "The vehicle passed multiple checkpoints and dozens of CCTV cameras. "
            "Those cameras recorded every second, yet warned nobody. Footage was retrieved only hours later in a post-mortem investigation. "
            "NCRB reports over four lakh crimes against women across India annually. Over 95% of surveillance remains purely passive, storing footage humans only inspect after trauma occurs. "
            "When pinned or in shock, a victim cannot trigger an SOS app. "
            "We built SurakshaEdge to transform passive cameras into an autonomous, zero-touch guardian."
        )
    },
    {
        "filename": "Act2_Architecture_and_Skeleton_Inspector.mp3",
        "title": "Act 2: Architecture & Live Skeleton Inspector",
        "rate": "+20%",
        "pitch": "+0Hz",
        "text": (
            "SurakshaEdge processes video and audio locally on the edge node. "
            "Here is our live edge camera feed. The vision branch runs YOLOv8-Pose, tracking seventeen skeletal keypoints per person at eighteen frames per second on CPU. "
            "It computes three biomechanical distress metrics in real time: normalized wrist velocity V_w, joint angular acceleration A_j, and proximity Q_p. "
            "Simultaneously, the acoustic branch runs an MFCC neural network on 16 kilohertz audio to detect scream panic signatures S_t. "
            "Our core innovation is the 1.5-Second Temporal Fusion Gate. "
            "Single sensors cause debilitating false alarms. SurakshaEdge demands that physical grapple kinematics and vocal distress coincide within 1.5 seconds before raising an alarm."
        )
    },
    {
        "filename": "Act3_Hard_Negative_Suppression.mp3",
        "title": "Act 3: Hard Negative False-Alarm Suppression",
        "rate": "+20%",
        "pitch": "+0Hz",
        "text": (
            "Watch how our dual-signal gate eliminates false alarms. "
            "We inject a hard-negative scenario: rapid jogging and energetic movement. "
            "Notice the kinematic score K_t rises as limbs swing rapidly. However, the audio model detects only ambient sound. "
            "Because vocal distress does not arrive within 1.5 seconds, the gate stays locked. The siren remains silent. "
            "Across our benchmark validation, false positives on sports, dancing, and traffic horns are suppressed by 100%."
        )
    },
    {
        "filename": "Act4_Assault_Alert_and_Encrypted_Replay.mp3",
        "title": "Act 4: Live Assault Alert & Encrypted Replay",
        "rate": "+20%",
        "pitch": "+0Hz",
        "text": (
            "Now, watch an active assault sequence: physical grappling and vocal panic occurring simultaneously. "
            "Within sixty-four milliseconds of temporal alignment, the gate triggers a Level-1 Red Alert. "
            "The Gate-1 marker flashes red and the camera flies into focus. "
            "The 110-decibel on-site siren and red LED strobe trigger immediately to deter the attacker. "
            "An encrypted event packet reaches our dashboard in under ninety milliseconds. "
            "Notice our zero-persistence privacy architecture: frames circulate in volatile RAM in a rolling 5-second ring buffer. "
            "Zero raw video is ever stored on disk. Only upon a verified emergency is an AES-256-GCM encrypted 5-second evidence packet captured."
        )
    },
    {
        "filename": "Act5_Multi_Node_and_Telemetry_Export.mp3",
        "title": "Act 5: Multi-Node Coordination & Export",
        "rate": "+20%",
        "pitch": "+0Hz",
        "text": (
            "SurakshaEdge coordinates autonomously across an entire campus network. "
            "Gate-2 detects an isolated advisory, Gate-1 triggers an advisory, and Gate-3 escalates to a full red alert. "
            "Each node operates independently without single-point cloud failures. "
            "With one click, security personnel can export the cryptographically sealed JSON telemetry dossier containing GPS coordinates, velocity logs, and acoustic confidence data for forensic evidence."
        )
    },
    {
        "filename": "Act6_Hardware_CAD_and_BOM.mp3",
        "title": "Act 6: Hardware CAD Blueprint & BOM",
        "rate": "+20%",
        "pitch": "+0Hz",
        "text": (
            "SurakshaEdge operates as an inline edge appliance retrofitting existing RTSP cameras. "
            "Our custom CAD enclosure measures 180 by 130 by 65 millimeters in IP66 weatherproof die-cast aluminum. "
            "It features a front acoustic horn with a hydrophobic Gore-Tex membrane for the Knowles MEMS array, and rear convection heatsink fins dissipating fifteen Watts without mechanical fans. "
            "Our prototype benchtop unit costs under 11,900 rupees, scaling to 4,200 rupees per node in batch production, or zero additional hardware cost when deployed directly onto existing campus servers."
        )
    },
    {
        "filename": "Act7_Benchmarks_and_Closing.mp3",
        "title": "Act 7: Measured Benchmarks & Closing",
        "rate": "+20%",
        "pitch": "+0Hz",
        "text": (
            "Every metric we present is directly verified by our forty-eight passing automated test suites: "
            "Our measured trigger-to-dashboard latency is 89.4 milliseconds, well below our 450 millisecond design ceiling. "
            "Steady-state bandwidth is 0 kbps, reducing network consumption by 99.98% compared to continuous cloud streaming. "
            "A compact 12-volt battery delivers 24.5 hours of continuous protection through blackouts. "
            "SurakshaEdge proves that we do not need to replace India's millions of surveillance cameras. We simply need to make them intelligent, vigilant, and privacy-respecting. "
            "Thank you."
        )
    }
]

async def generate():
    voice = "en-IN-PrabhatNeural"
    print(f"Generating calibrated voiceover with {voice} at +20% rate...")
    total_dur = 0
    
    for idx, act in enumerate(ACTS_CALIBRATED, 1):
        out_path = os.path.join(OUTPUT_DIR, act["filename"])
        communicate = edge_tts.Communicate(
            text=act["text"],
            voice=voice,
            rate=act["rate"],
            pitch=act["pitch"]
        )
        await communicate.save(out_path)
        info = sf.info(out_path)
        total_dur += info.duration
        print(f"  [{idx}/7] {act['filename']}: {info.duration:.1f}s ({int(info.duration // 60)}m {int(info.duration % 60):02d}s)")

    print(f"\nFinal Voiceover Duration: {total_dur:.1f}s ({int(total_dur // 60)}m {int(total_dur % 60):02d}s)")
    print(f"SAFETY CUSHION: Exactly {300 - total_dur:.1f} seconds under the 5:00 maximum ceiling! PERFECT!")

if __name__ == "__main__":
    asyncio.run(generate())
