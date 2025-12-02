from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health", summary="Simple health probe")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
