from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ReservationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ChargingSession(Base):
    __tablename__ = "charging_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)

    reservations = relationship("Reservation", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"ChargingSession(id={self.id!r}, name={self.name!r})"


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        UniqueConstraint("session_id", "start_time", name="uq_reservation_session_start"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(Integer, ForeignKey("charging_sessions.id"), nullable=False, index=True)
    plate = Column(String(32), nullable=False, index=True)
    plate_normalized = Column(String(32), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(SAEnum(ReservationStatus, name="reservation_status"), nullable=False, default=ReservationStatus.CONFIRMED)
    contact_email = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    session = relationship("ChargingSession", back_populates="reservations")
    slots = relationship(
        "ReservationSlot",
        back_populates="reservation",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"Reservation(id={self.id!r}, session_id={self.session_id!r}, plate={self.plate!r}, "
            f"start_time={self.start_time!r}, end_time={self.end_time!r}, status={self.status!r}, "
            f"contact_email={self.contact_email!r})"
        )

    @property
    def derived_status(self) -> ReservationStatus:
        now = datetime.now(timezone.utc)
        if self.status == ReservationStatus.CANCELLED:
            return ReservationStatus.CANCELLED

        start = self.start_time
        end = self.end_time
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        if now < start:
            return ReservationStatus.CONFIRMED
        if start <= now < end:
            return ReservationStatus.IN_PROGRESS
        return ReservationStatus.COMPLETED


class ReservationSlot(Base):
    __tablename__ = "reservation_slots"
    __table_args__ = (UniqueConstraint("session_id", "slot_start", name="uq_session_slot"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    reservation_id = Column(
        String(36),
        ForeignKey("reservations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = Column(Integer, ForeignKey("charging_sessions.id"), nullable=False, index=True)
    slot_start = Column(DateTime(timezone=True), nullable=False, index=True)

    reservation = relationship("Reservation", back_populates="slots")

    def __repr__(self) -> str:
        return (
            f"ReservationSlot(id={self.id!r}, reservation_id={self.reservation_id!r}, "
            f"session_id={self.session_id!r}, slot_start={self.slot_start!r})"
        )
