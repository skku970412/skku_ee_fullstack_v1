from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from typing import Tuple
from zoneinfo import ZoneInfo

from .config import get_settings

UTC = timezone.utc


@lru_cache(1)
def business_timezone() -> ZoneInfo:
    """Return the configured business timezone."""
    settings = get_settings()
    return ZoneInfo(settings.business_timezone)


def combine_business_datetime(date_value: date, time_value: time) -> datetime:
    """Combine date and time as a timezone-aware datetime in the business timezone."""
    naive_dt = datetime.combine(date_value, time_value.replace(tzinfo=None))
    return naive_dt.replace(tzinfo=business_timezone())


def business_day_bounds_utc(date_value: date) -> Tuple[datetime, datetime]:
    """Return the UTC start (inclusive) and end (exclusive) datetimes for the business day."""
    start_local = combine_business_datetime(date_value, time.min)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Coerce the datetime into UTC; naive datetimes are treated as UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_business_local(dt: datetime) -> datetime:
    """Convert a datetime to the business timezone for presentation."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(business_timezone())
