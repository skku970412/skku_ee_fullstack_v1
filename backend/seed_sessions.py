from __future__ import annotations

import argparse

from app import crud
from app.database import SessionLocal


def main(names: list[str]) -> None:
    with SessionLocal() as session:
        crud.ensure_base_sessions(session, names=names)
        session.commit()
    print(f"Seeded {len(names)} sessions (id 1..{len(names)}).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed default charging sessions.")
    parser.add_argument(
        "--count",
        type=int,
        default=4,
        help="Number of sessions to create (defaults to 4).",
    )
    args = parser.parse_args()
    sessions = [f"세션 {idx}" for idx in range(1, args.count + 1)]
    main(sessions)
