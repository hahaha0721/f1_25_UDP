#!/usr/bin/env python3
"""A small, intentionally non-official UDP telemetry generator."""

from __future__ import annotations

import argparse
import json
import random
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send simulated racing telemetry as JSON over UDP."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Receiver IP address")
    parser.add_argument("--port", type=int, default=20777, help="Receiver UDP port")
    parser.add_argument("--laps", type=int, default=3, help="Number of laps to simulate")
    parser.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help="Seconds between telemetry packets",
    )
    parser.add_argument(
        "--updates-per-lap",
        type=int,
        default=20,
        help="Telemetry updates generated during each lap",
    )
    parser.add_argument("--driver", default="Practice Driver", help="Driver name")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def send_packet(
    sock: socket.socket,
    target: tuple[str, int],
    sequence: int,
    packet_type: str,
    session_id: str,
    data: dict[str, Any],
) -> None:
    packet = {
        "version": 1,
        "type": packet_type,
        "sequence": sequence,
        "session_id": session_id,
        "sent_at": utc_now(),
        "data": data,
    }
    payload = json.dumps(packet, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    sock.sendto(payload, target)
    print(
        f"sent #{sequence:<3} {packet_type:<16} "
        f"{len(payload):>4} bytes -> {target[0]}:{target[1]}"
    )


def main() -> None:
    args = parse_args()
    if args.laps < 1:
        raise SystemExit("--laps must be at least 1")
    if args.interval < 0:
        raise SystemExit("--interval cannot be negative")
    if args.updates_per_lap < 1:
        raise SystemExit("--updates-per-lap must be at least 1")

    rng = random.Random(args.seed)
    target = (args.host, args.port)
    session_id = str(uuid.uuid4())
    sequence = 0
    completed_laps: list[int] = []

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        send_packet(
            sock,
            target,
            sequence,
            "session_start",
            session_id,
            {
                "track": "Practice Circuit",
                "driver": args.driver,
                "total_laps": args.laps,
            },
        )
        sequence += 1

        for lap_number in range(1, args.laps + 1):
            target_lap_ms = rng.randint(88_000, 96_000)

            for update in range(1, args.updates_per_lap + 1):
                progress = update / args.updates_per_lap
                elapsed_ms = round(target_lap_ms * progress)
                speed_kph = round(rng.uniform(120, 330), 1)

                send_packet(
                    sock,
                    target,
                    sequence,
                    "telemetry",
                    session_id,
                    {
                        "driver": args.driver,
                        "lap": lap_number,
                        "lap_progress": round(progress, 3),
                        "current_lap_time_ms": elapsed_ms,
                        "speed_kph": speed_kph,
                        "throttle": round(rng.random(), 3),
                        "brake": round(rng.random(), 3),
                    },
                )
                sequence += 1
                time.sleep(args.interval)

            completed_laps.append(target_lap_ms)
            send_packet(
                sock,
                target,
                sequence,
                "lap_complete",
                session_id,
                {
                    "driver": args.driver,
                    "lap": lap_number,
                    "lap_time_ms": target_lap_ms,
                    "is_valid": True,
                    "best_lap_ms": min(completed_laps),
                },
            )
            sequence += 1

        send_packet(
            sock,
            target,
            sequence,
            "session_end",
            session_id,
            {
                "driver": args.driver,
                "completed_laps": args.laps,
                "best_lap_ms": min(completed_laps),
                "all_lap_times_ms": completed_laps,
            },
        )


if __name__ == "__main__":
    main()
