from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, status

from ..schemas import UserLoginRequest, UserLoginResponse

router = APIRouter(prefix="/api/user", tags=["user"])


@router.post("/login", response_model=UserLoginResponse, summary="사용자 로그인 (데모)")
def user_login(payload: UserLoginRequest) -> UserLoginResponse:
    if not payload.email or not payload.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이메일과 비밀번호를 입력하세요.",
        )
    token = secrets.token_urlsafe(24)
    return UserLoginResponse(token=token, user={"email": payload.email})
