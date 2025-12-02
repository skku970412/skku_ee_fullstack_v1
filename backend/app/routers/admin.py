from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud
from ..config import get_settings
from ..database import get_db
from ..schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    ReservationDeleteResponse,
    SessionReservations,
    SessionsResponse,
)
from .reservations import to_reservation_public

settings = get_settings()

router = APIRouter(prefix="/api/admin", tags=["admin"])


def verify_admin_token(authorization: str = Header(..., alias="Authorization")) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 관리자 토큰입니다.")
    return token


@router.post("/login", response_model=AdminLoginResponse, summary="관리자 로그인")
def admin_login(payload: AdminLoginRequest) -> AdminLoginResponse:
    if payload.email != settings.admin_email or payload.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    return AdminLoginResponse(token=settings.admin_token, admin={"email": payload.email})


@router.get(
    "/reservations/by-session",
    response_model=SessionsResponse,
    summary="관리자용 세션 예약 조회",
)
def admin_reservations_by_session(
    target_date: date = Query(..., alias="date", description="조회 날짜 (YYYY-MM-DD)"),
    _: str = Depends(verify_admin_token),
    db: Session = Depends(get_db),
) -> SessionsResponse:
    sessions = crud.list_sessions(db)
    result: list[SessionReservations] = []
    for session_obj in sessions:
        reservations = crud.reservations_by_session_and_date(
            db, session_id=session_obj.id, date_value=target_date
        )
        result.append(
            SessionReservations(
                sessionId=session_obj.id,
                name=session_obj.name,
                reservations=[to_reservation_public(res) for res in reservations],
            )
        )
    return SessionsResponse(sessions=result)


@router.delete(
    "/reservations/{reservation_id}",
    response_model=ReservationDeleteResponse,
    summary="예약 삭제",
)
def delete_reservation(
    reservation_id: str,
    _: str = Depends(verify_admin_token),
    db: Session = Depends(get_db),
) -> ReservationDeleteResponse:
    deleted = crud.delete_reservation(db, reservation_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="예약을 찾을 수 없습니다.")
    return ReservationDeleteResponse()
