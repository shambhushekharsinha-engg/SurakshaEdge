"""
SurakshaEdge Demo Injector
Posts a synthetic sequence of events to the running API to demonstrate
the alert pipeline end-to-end without a real camera.

Usage:
    python scripts/demo_injector.py --url http://127.0.0.1:8000 --token demo-token
    python scripts/demo_injector.py --dry-run  # validate without POSTing
"""
from __future__ import annotations

import argparse
import datetime
import sys
import time
import uuid


def make_event(camera_id: str, tier: str, K_t: float, S_t: float, dt_s: float, gps: dict) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "camera_id": camera_id,
        "ts_utc": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "tier": tier,
        "gps": gps,
        "scores": {"K_t": K_t, "S_t": S_t, "dt_s": max(dt_s, 0.0)},
        "bboxes": [],
        "clip_enc": None,
        "latency_ms": {"pipeline": 32.0, "dispatch": 4.0},
    }


SCENARIO = [
    # (delay_s, tier, K_t, S_t, dt_s, note)
    (0.0,  "ADVISORY", 0.63, 0.00, -1.0, "K_t rising — possible struggle"),
    (1.2,  "ADVISORY", 0.71, 0.00, -1.0, "K_t sustained high"),
    (2.4,  "ADVISORY", 0.76, 0.45, -1.0, "S_t building"),
    (3.0,  "ALERT",    0.78, 0.85,  0.8, "ALERT — K + S within gate window"),
    (4.2,  "ADVISORY", 0.65, 0.30, -1.0, "Post-alert cooldown"),
    (5.5,  "ADVISORY", 0.52, 0.10, -1.0, "Situation de-escalating"),
]

# Extended demo_video scenario — optimized for 5-minute pitch recording
SCENARIO_DEMO_VIDEO = [
    (0.0,  "ADVISORY", 0.45, 0.00, -1.0, "Normal activity — monitoring"),
    (1.5,  "ADVISORY", 0.63, 0.00, -1.0, "K_t rising — possible struggle"),
    (3.0,  "ADVISORY", 0.72, 0.40, -1.0, "S_t building — visual conflict sustained"),
    (4.2,  "ALERT",    0.78, 0.85,  0.8, "DUAL-SIGNAL FUSION ALERT ⚡"),
    (6.0,  "ADVISORY", 0.65, 0.30, -1.0, "Post-alert cooldown"),
    (9.0,  "ADVISORY", 0.40, 0.10, -1.0, "Situation de-escalating"),
]

CAMERAS = {
    "gate-1": {"lat": 28.4600, "lon": 77.4952},
    "gate-2": {"lat": 28.4614, "lon": 77.4960},
    "gate-3": {"lat": 28.4586, "lon": 77.4950},
}


def main():
    parser = argparse.ArgumentParser(description="SurakshaEdge demo event injector")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--token", default="demo-token", help="Bearer token")
    parser.add_argument("--camera", default="gate-1", choices=list(CAMERAS.keys()))
    parser.add_argument("--dry-run", action="store_true", help="Print events without POSTing")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat the scenario N times")
    parser.add_argument("--scenario", default="default", choices=["default", "demo_video"],
                        help="Scenario to run: 'default' or 'demo_video' (video-pitch optimized)")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — events that would be posted:")
        gps = CAMERAS[args.camera]
        active_scenario = SCENARIO_DEMO_VIDEO if args.scenario == "demo_video" else SCENARIO
        for delay, tier, K_t, S_t, dt_s, note in active_scenario:
            evt = make_event(args.camera, tier, K_t, S_t, dt_s, gps)
            print(f"  t+{delay:.1f}s  [{tier:8s}]  K_t={K_t:.2f}  S_t={S_t:.2f}  # {note}")
        print(f"\nTotal events: {len(active_scenario)} per cycle, {args.repeat} cycle(s)")
        return

    try:
        import requests
    except ImportError:
        print("ERROR: requests package required. pip install requests", file=sys.stderr)
        sys.exit(1)

    gps = CAMERAS[args.camera]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {args.token}",
    }

    active_scenario = SCENARIO_DEMO_VIDEO if args.scenario == "demo_video" else SCENARIO
    scenario_name = "demo_video" if args.scenario == "demo_video" else "default"
    print(f"\nRunning scenario '{scenario_name}' on camera '{args.camera}' x{args.repeat}")

    for cycle in range(args.repeat):
        if args.repeat > 1:
            print(f"\n── Cycle {cycle + 1}/{args.repeat} ──")
        start = time.time()
        for delay, tier, K_t, S_t, dt_s, note in active_scenario:
            # Wait until the right time in the scenario
            elapsed = time.time() - start
            wait = delay - elapsed
            if wait > 0:
                time.sleep(wait)

            evt = make_event(args.camera, tier, K_t, S_t, dt_s, gps)
            tag = f"[{tier:8s}]"
            try:
                resp = requests.post(f"{args.url}/events", headers=headers, json=evt, timeout=5)
                status_str = f"HTTP {resp.status_code}"
                ok = "✅" if resp.status_code == 201 else "⚠"
            except Exception as e:
                status_str = f"ERROR: {e}"
                ok = "❌"
            print(f"  t+{delay:.1f}s {ok} {tag} K_t={K_t:.2f} S_t={S_t:.2f}  {status_str}  # {note}")

    print("\nDemo injection complete.")


if __name__ == "__main__":
    main()
