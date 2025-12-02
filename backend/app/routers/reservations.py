from __future__ import annotations

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_db
from ..models import ChargingSession, Reservation, ReservationStatus
from ..schemas import (
    PlateMatchRequest,
    PlateMatchResponse,
    PlateVerificationRequest,
    PlateVerificationResponse,
    ReservationCreate,
    ReservationBatchCreate,
    ReservationDeleteResponse,
    ReservationPublic,
    SessionReservations,
    SessionsResponse,
)
from ..time_utils import (
    UTC,
    combine_business_datetime,
    to_business_local,
)

router = APIRouter(prefix="/api", tags=["reservations"])

SLOT_MINUTES = 30


def to_reservation_public(reservation: Reservation) -> ReservationPublic:
    start_local = to_business_local(reservation.start_time)
    end_local = to_business_local(reservation.end_time)
    return ReservationPublic(
        id=reservation.id,
        sessionId=reservation.session_id,
        plate=reservation.plate,
        date=start_local.date(),
        startTime=start_local.time().replace(second=0, microsecond=0, tzinfo=None),
        endTime=end_local.time().replace(second=0, microsecond=0, tzinfo=None),
        status=reservation.derived_status,
        contactEmail=reservation.contact_email,
    )


@router.get("/sessions", response_model=list[SessionReservations], summary="충전 세션 목록")
def list_sessions(db: Session = Depends(get_db)) -> list[SessionReservations]:
    sessions = crud.list_sessions(db)
    return [
        SessionReservations(
            sessionId=session.id,
            name=session.name,
            reservations=[
                to_reservation_public(reservation)
                for reservation in sorted(session.reservations, key=lambda r: r.start_time)
            ],
        )
        for session in sessions
    ]


@router.get(
    "/reservations/by-session",
    response_model=SessionsResponse,
    summary="날짜별 세션 예약 현황",
)
def list_reservations_by_session(
    target_date: date = Query(..., alias="date", description="조회할 날짜 (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
) -> SessionsResponse:
    sessions = crud.list_sessions(db)
    payload: list[SessionReservations] = []
    for session_obj in sessions:
        reservations = crud.reservations_by_session_and_date(
            db, session_id=session_obj.id, date_value=target_date
        )
        payload.append(
            SessionReservations(
                sessionId=session_obj.id,
                name=session_obj.name,
                reservations=[to_reservation_public(res) for res in reservations],
            )
        )
    return SessionsResponse(sessions=payload)


@router.post(
    "/reservations",
    response_model=ReservationPublic,
    status_code=status.HTTP_201_CREATED,
    summary="예약 생성",
)
def create_reservation(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
) -> ReservationPublic:
    session_obj: ChargingSession | None = db.get(ChargingSession, payload.session_id)
    if session_obj is None:
        raise HTTPException(status_code=404, detail='해당 세션을 찾을 수 없습니다.')

    start_local = combine_business_datetime(payload.date, payload.start_time)
    end_local = combine_business_datetime(payload.date, payload.end_time)
    if end_local <= start_local and payload.end_time == time(0, 0):
        end_local = end_local + timedelta(days=1)
    if end_local <= start_local:
        raise HTTPException(status_code=400, detail='종료 시간이 시작 시간보다 빠릅니다.')

    def _is_valid_slot(dt: datetime) -> bool:
        return dt.minute in (0, 30) and dt.second == 0 and dt.microsecond == 0

    if not _is_valid_slot(start_local) or not _is_valid_slot(end_local):
        raise HTTPException(status_code=400, detail='예약은 30분 단위로만 가능합니다.')


    duration_minutes = int((end_local - start_local).total_seconds() / 60)
    if duration_minutes % SLOT_MINUTES != 0:
        raise HTTPException(status_code=400, detail='예약은 30분 배수 길이로만 가능합니다.')

    start_dt = start_local.astimezone(UTC)
    end_dt = end_local.astimezone(UTC)

    try:
        reservation = crud.create_reservation(
            db,
            session_id=session_obj.id,
            plate=payload.plate,
            start_time=start_dt,
            end_time=end_dt,
            contact_email=payload.contact_email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return to_reservation_public(reservation)


@router.post(
    "/reservations/batch",
    response_model=list[ReservationPublic],
    status_code=status.HTTP_201_CREATED,
    summary="다수 1시간 예약 생성",
)
def create_reservations_batch(
    payload: ReservationBatchCreate,
    db: Session = Depends(get_db),
) -> list[ReservationPublic]:
    session_obj: ChargingSession | None = db.get(ChargingSession, payload.session_id)
    if session_obj is None:
        raise HTTPException(status_code=404, detail="?? ??? ?? ? ????.")
    if not payload.start_times:
        raise HTTPException(status_code=400, detail="startTimes? ?? ????.")

    duration_minutes = 60

    def _is_valid_slot(dt: datetime) -> bool:
        return dt.minute in (0, 30) and dt.second == 0 and dt.microsecond == 0

    created: list[Reservation] = []
    try:
        for start_time_value in sorted(payload.start_times):
            start_local = combine_business_datetime(payload.date, start_time_value)
            end_local = start_local + timedelta(minutes=duration_minutes)

            if end_local <= start_local:
                raise HTTPException(status_code=400, detail="?? ??? ?? ???? ????.")
            if not _is_valid_slot(start_local) or not _is_valid_slot(end_local):
                raise HTTPException(status_code=400, detail="??? 30? ???? ?????.")

            start_dt = start_local.astimezone(UTC)
            end_dt = end_local.astimezone(UTC)

            reservation = crud.create_reservation(
                db,
                session_id=session_obj.id,
                plate=payload.plate,
                start_time=start_dt,
                end_time=end_dt,
                contact_email=payload.contact_email,
            )
            created.append(reservation)
    except HTTPException:
        db.rollback()
        raise
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [to_reservation_public(reservation) for reservation in created]
@router.post(
    "/plates/verify",
    response_model=PlateVerificationResponse,
    summary="차량 번호 중복/형식 확인",
)
def verify_plate(
    payload: PlateVerificationRequest,
    db: Session = Depends(get_db),
) -> PlateVerificationResponse:
    normalized_plate = crud.normalize_plate(payload.plate)
    start_dt = end_dt = None
    if payload.date and payload.start_time and payload.end_time:
        start_local = combine_business_datetime(payload.date, payload.start_time)
        end_local = combine_business_datetime(payload.date, payload.end_time)
        if end_local <= start_local and payload.end_time == time(0, 0):
            end_local = end_local + timedelta(days=1)
        start_dt = start_local.astimezone(UTC)
        end_dt = end_local.astimezone(UTC)
    conflict = crud.find_conflicting_plate_reservation(
        db, plate=normalized_plate, start=start_dt, end=end_dt
    )
    if conflict:
        message = '해당 차량은 요청한 시간대에 이미 예약되어 있습니다.'
        conflict_public = to_reservation_public(conflict)
        return PlateVerificationResponse(
            valid=False,
            conflict=True,
            message=message,
            conflictingReservation=conflict_public,
        )

    message = '예약이 가능합니다.'
    return PlateVerificationResponse(valid=True, message=message)


@router.post(
    "/plates/match",
    response_model=PlateMatchResponse,
    summary="탐지된 차량 번호와 예약 매칭",
)
def match_detected_plate(
    payload: PlateMatchRequest,
    db: Session = Depends(get_db),
) -> PlateMatchResponse:
    reservation = crud.find_active_reservation_by_plate(
        db, plate=payload.plate, when=payload.timestamp
    )
    if reservation:
        return PlateMatchResponse(
            plate=payload.plate,
            match=True,
            reservation=to_reservation_public(reservation),
        )
    return PlateMatchResponse(plate=payload.plate, match=False)

@router.get(
    "/reservations/my",
    response_model=list[ReservationPublic],
    summary="사용자 예약 목록 조회",
)
def my_reservations(
    email: str | None = Query(None, description="예약 등록 이메일"),
    plate: str | None = Query(None, description="차량 번호"),
    db: Session = Depends(get_db),
) -> list[ReservationPublic]:
    if not email and not plate:
        raise HTTPException(status_code=400, detail="email 또는 plate를 제공해야 합니다.")
    try:
        reservations = crud.reservations_for_user(db, email=email, plate=plate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [to_reservation_public(reservation) for reservation in reservations]


@router.delete(
    "/reservations/{reservation_id}",
    response_model=ReservationDeleteResponse,
    summary="사용자 예약 삭제",
)
def delete_reservation_for_user(
    reservation_id: str,
    email: str | None = Query(None, description="예약 등록 이메일"),
    plate: str | None = Query(None, description="차량 번호"),
    db: Session = Depends(get_db),
) -> PlateVerificationResponse:
    if not email and not plate:
        raise HTTPException(status_code=400, detail="email 또는 plate를 제공해야 합니다.")
    try:
        deleted = crud.delete_reservation_for_user(
            db, reservation_id=reservation_id, email=email, plate=plate
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="예약을 찾을 수 없습니다.")
    return ReservationDeleteResponse()
