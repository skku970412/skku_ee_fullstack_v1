"""Quick helper to verify license-plate recognition and DB match in one go.

Usage:
  ./.venv/Scripts/python tools/test_plate_match.py --image example.jpg
  ./.venv/Scripts/python tools/test_plate_match.py --plate 12가3456 --timestamp 2025-11-22T18:45:00Z

Notes:
  - Requires OPENAI_API_KEY in the environment when using GPT-based recognition.
  - If --timestamp is omitted, the script uses the most recent reservation's mid-time.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi.testclient import TestClient
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.database import SessionLocal  # type: ignore  # noqa: E402
from backend.app.main import create_app  # type: ignore  # noqa: E402
from backend.app.models import Reservation  # type: ignore  # noqa: E402
from backend.app.time_utils import to_business_local  # type: ignore  # noqa: E402


@dataclass
class LatestReservation:
    plate: str
    start_utc: datetime
    end_utc: datetime

    @property
    def midpoint_utc(self) -> datetime:
        return self.start_utc + (self.end_utc - self.start_utc) / 2


def load_latest_reservation() -> Optional[LatestReservation]:
    with SessionLocal() as session:
        res: Reservation | None = (
            session.query(Reservation).order_by(Reservation.start_time.desc()).first()
        )
        if not res:
            return None
        return LatestReservation(
            plate=res.plate,
            start_utc=res.start_time,
            end_utc=res.end_time,
        )

def load_latest_for_plate(normalized_plate: str) -> Optional[LatestReservation]:
    with SessionLocal() as session:
        res: Reservation | None = (
            session.query(Reservation)
            .filter(Reservation.plate_normalized == normalized_plate)
            .order_by(Reservation.start_time.desc())
            .first()
        )
        if not res:
            return None
        return LatestReservation(
            plate=res.plate,
            start_utc=res.start_time,
            end_utc=res.end_time,
        )


def run(args: argparse.Namespace) -> None:
    # Ensure the app uses GPT API mode unless explicitly overridden outside.
    os.environ.setdefault("PLATE_SERVICE_MODE", "gptapi")

    app = create_app()
    client = TestClient(app)

    # If caller wants to force latest reservation plate/time, honor that first.
    plate_value = args.plate
    timestamp_override: datetime | None = None
    if args.use_latest:
        latest = load_latest_reservation()
        if not latest:
            raise SystemExit("No reservations found; cannot use --use-latest.")
        plate_value = latest.plate
        timestamp_override = latest.midpoint_utc
        local_start = to_business_local(latest.start_utc)
        local_end = to_business_local(latest.end_utc)
        print(
            "[latest] plate:", plate_value,
            "| window:", f"{local_start} -> {local_end} (local)",
            "| midpoint UTC:", timestamp_override,
        )

    if not plate_value:
        image_path = Path(args.image)
        if not image_path.exists():
            raise SystemExit(f"Image not found: {image_path}")

        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY is missing; set it before running recognition.")

        files = {
            "image": (
                image_path.name,
                image_path.read_bytes(),
                "image/jpeg",
            )
        }
        resp = client.post("/api/license-plates", files=files)
        print("[recognition] status:", resp.status_code)
        try:
            body = resp.json()
        except Exception as exc:  # pylint: disable=broad-except
            raise SystemExit(f"[recognition] invalid response: {exc}") from exc
        try:
            import json

            print("[recognition] body:", json.dumps(body, ensure_ascii=False))
        except Exception:
            print("[recognition] body:", body)
        if resp.status_code != 200 or "plate" not in body:
            raise SystemExit("Recognition failed; aborting match test.")
        plate_value = body["plate"]

    # Choose timestamp
    if timestamp_override:
        timestamp = timestamp_override
    elif args.timestamp:
        timestamp = datetime.fromisoformat(args.timestamp.replace("Z", "+00:00"))
    else:
        # Try to pick a reservation that matches the plate first.
        candidate: LatestReservation | None = None
        if plate_value:
            candidate = load_latest_for_plate(plate_value.replace(" ", "").upper())
        if not candidate:
            candidate = load_latest_reservation()
        if not candidate:
            raise SystemExit("No reservations found; provide --timestamp manually.")
        timestamp = candidate.midpoint_utc
        local_start = to_business_local(candidate.start_utc)
        local_end = to_business_local(candidate.end_utc)
        print(
            "[timestamp] using reservation window",
            f"{local_start} -> {local_end} (local), midpoint UTC {timestamp}",
        )

    payload = {"plate": plate_value, "timestamp": timestamp.isoformat()}
    resp = client.post("/api/plates/match", json=payload)
    print("[match] status:", resp.status_code)
    try:
        match_body = resp.json()
    except Exception as exc:  # pylint: disable=broad-except
        raise SystemExit(f"[match] invalid response: {exc}") from exc
    try:
        import json

        print("[match] body:", json.dumps(match_body, ensure_ascii=False))
    except Exception:
        print("[match] body:", match_body)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test plate recognition and DB match together.")
    parser.add_argument(
        "--image",
        default="example.jpg",
        help="Image file to upload when plate is not provided (default: example.jpg).",
    )
    parser.add_argument(
        "--plate",
        help="Skip recognition and use this plate string directly.",
    )
    parser.add_argument(
        "--timestamp",
        help=(
            "ISO8601 timestamp for match check. If omitted, uses the latest reservation's midpoint "
            "(UTC)."
        ),
    )
    parser.add_argument(
        "--use-latest",
        action="store_true",
        help="Skip recognition and use the latest reservation's plate + midpoint timestamp.",
    )
    return parser


if __name__ == "__main__":
    run(build_parser().parse_args())
