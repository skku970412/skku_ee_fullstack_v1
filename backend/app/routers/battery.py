from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from ..config import get_settings
from ..schemas import BatteryStatusResponse

router = APIRouter(prefix="/api/battery", tags=["battery"])


def _parse_timestamp(value) -> datetime | None:
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            divisor = 1000.0 if abs(value) > 1_000_000_000 else 1.0
            return datetime.fromtimestamp(value / divisor, tz=timezone.utc)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if stripped.isdigit():
                return _parse_timestamp(int(stripped))
            normalized = stripped[:-1] + "+00:00" if stripped.endswith("Z") else stripped
            return datetime.fromisoformat(normalized)
    except Exception:
        return None
    return None


@router.get(
    "/now",
    response_model=BatteryStatusResponse,
    summary="Latest battery status from Firebase RTDB",
)
async def get_battery_status_now(
    settings=Depends(get_settings),
) -> BatteryStatusResponse:
    if not settings.battery_rtdb_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Battery RTDB URL is not configured.",
        )

    base = settings.battery_rtdb_url.rstrip("/")
    path = settings.battery_rtdb_path or "/car-battery-now"
    url = f"{base}/{path.lstrip('/')}.json"
    params = {"auth": settings.battery_rtdb_auth} if settings.battery_rtdb_auth else None

    try:
        timeout = httpx.Timeout(8.0, connect=4.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, params=params)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"RTDB request failed: {exc.__class__.__name__}",
        ) from exc

    if resp.status_code == status.HTTP_401_UNAUTHORIZED:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="RTDB auth failed (401).",
        )
    if resp.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="RTDB path not found.",
        )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"RTDB error: status {resp.status_code}",
        )

    try:
        data = resp.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid RTDB response.",
        ) from exc

    percent = None
    voltage = None
    timestamp = None
    if isinstance(data, dict):
        if isinstance(data.get("percent"), (int, float)):
            percent = float(data["percent"])
        if isinstance(data.get("voltage"), (int, float)):
            voltage = float(data["voltage"])
        timestamp = _parse_timestamp(data.get("timestamp"))

    return BatteryStatusResponse(
        percent=percent,
        voltage=voltage,
        timestamp=timestamp,
    )
