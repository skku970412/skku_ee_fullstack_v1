from __future__ import annotations

import datetime as dt
from datetime import date, datetime, time, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import ReservationStatus


class ReservationCreate(BaseModel):
    session_id: int = Field(..., alias="sessionId")
    plate: str
    date: date
    start_time: time = Field(..., alias="startTime")
    end_time: time = Field(..., alias="endTime")
    contact_email: str | None = Field(None, alias="contactEmail")

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    @field_validator("plate")
    @classmethod
    def validate_plate(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("차량 번호가 너무 짧습니다.")
        return normalized

    @field_validator("contact_email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        email = value.strip()
        if not email:
            return None
        return email.lower()

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, value: Any) -> date:
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d").date()
        raise ValueError("유효한 날짜 형식이 아닙니다.")

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_time(cls, value: Any) -> time:
        if isinstance(value, time):
            return value
        if isinstance(value, str):
            text = value.strip()
            if text == "24:00":
                return time(0, 0)
            try:
                return datetime.strptime(text, "%H:%M").time()
            except ValueError as exc:
                raise ValueError("Invalid time format.") from exc
        raise ValueError("Invalid time format.")


class ReservationBatchCreate(BaseModel):
    session_id: int = Field(..., alias="sessionId")
    plate: str
    date: date
    start_times: list[time] = Field(..., alias="startTimes")
    contact_email: str | None = Field(None, alias="contactEmail")

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    @field_validator("plate")
    @classmethod
    def validate_plate(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 5:
            raise ValueError("차량 번호가 너무 짧습니다.")
        return normalized

    @field_validator("contact_email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        email = value.strip()
        if not email:
            return None
        return email.lower()

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, value: Any) -> date:
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d").date()
        raise ValueError("잘못된 날짜 형식입니다.")

    @field_validator("start_times", mode="before")
    @classmethod
    def parse_times(cls, value: Any) -> list[time]:
        if isinstance(value, list):
            parsed: list[time] = []
            for item in value:
                if isinstance(item, time):
                    parsed.append(item)
                    continue
                if isinstance(item, str):
                    parsed.append(datetime.strptime(item, "%H:%M").time())
                    continue
                raise ValueError("잘못된 시간 형식입니다.")
            return parsed
        raise ValueError("startTimes는 리스트여야 합니다.")

    @field_validator("start_times")
    @classmethod
    def validate_times(cls, values: list[time]) -> list[time]:
        if not values:
            raise ValueError("startTimes가 비어 있습니다.")
        if len(set(values)) != len(values):
            raise ValueError("startTimes에 중복된 시간이 있습니다.")
        return values


class ReservationPublic(BaseModel):
    id: str
    session_id: int = Field(..., alias="sessionId")
    plate: str
    date: date
    start_time: time = Field(..., alias="startTime")
    end_time: time = Field(..., alias="endTime")
    status: ReservationStatus
    contact_email: str | None = Field(None, alias="contactEmail")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            date: lambda value: value.isoformat(),
            time: lambda value: value.strftime("%H:%M"),
        },
    )


class SessionReservations(BaseModel):
    session_id: int = Field(..., alias="sessionId")
    name: str
    reservations: list[ReservationPublic]

    model_config = ConfigDict(populate_by_name=True)


class SessionsResponse(BaseModel):
    sessions: list[SessionReservations]


class ReservationDeleteResponse(BaseModel):
    ok: bool = True


class ReservationsBatchResponse(BaseModel):
    reservations: list[ReservationPublic]


class PlateVerificationRequest(BaseModel):
    plate: str
    session_id: Optional[int] = Field(None, alias="sessionId")
    date: Optional[dt.date] = None
    start_time: Optional[time] = Field(None, alias="startTime")
    end_time: Optional[time] = Field(None, alias="endTime")

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, value: Any) -> Optional[date]:
        if value in (None, ""):
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return datetime.strptime(value, "%Y-%m-%d").date()
        raise ValueError("유효한 날짜 형식이 아닙니다.")

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def parse_time(cls, value: Any) -> Optional[time]:
        if value in (None, ""):
            return None
        if isinstance(value, time):
            return value
        if isinstance(value, str):
            text = value.strip()
            if text == "24:00":
                return time(0, 0)
            try:
                return datetime.strptime(text, "%H:%M").time()
            except ValueError as exc:
                raise ValueError("Invalid time format.") from exc
        raise ValueError("Invalid time format.")

class PlateVerificationResponse(BaseModel):
    valid: bool
    conflict: bool = False
    message: str
    conflictingReservation: Optional[ReservationPublic] = None


class PlateMatchRequest(BaseModel):
    plate: str
    timestamp: datetime

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if isinstance(value, (int, float)):
            divisor = 1000.0 if abs(value) > 1_000_000_000_000 else 1.0
            return datetime.fromtimestamp(value / divisor, tz=timezone.utc)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("timestamp 값이 비어 있습니다.")
            if stripped.isdigit():
                return cls.parse_timestamp(int(stripped))
            normalized = stripped[:-1] + "+00:00" if stripped.endswith("Z") else stripped
            return datetime.fromisoformat(normalized)
        raise ValueError("timestamp 형식을 해석할 수 없습니다.")


class PlateMatchResponse(BaseModel):
    plate: str
    match: bool
    reservation: Optional[ReservationPublic] = None


class AdminLoginRequest(BaseModel):
    email: str
    password: str

    model_config = ConfigDict(str_strip_whitespace=True)


class AdminLoginResponse(BaseModel):
    token: str
    admin: dict[str, str]


class UserLoginRequest(BaseModel):
    email: str
    password: str

    model_config = ConfigDict(str_strip_whitespace=True)


class UserLoginResponse(BaseModel):
    token: str
    user: dict[str, str]


class BatteryStatusResponse(BaseModel):
    percent: Optional[float] = None
    voltage: Optional[float] = None
    timestamp: Optional[datetime] = None
