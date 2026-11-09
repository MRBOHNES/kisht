from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.deps import current_user
from app.models import User
from app.security import COOKIE_NAME, DUMMY_HASH, make_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    branch_id: int


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role.value, branch_id=user.branch_id)


@router.post("/login", response_model=UserOut)
async def login(body: LoginIn, response: Response, session: AsyncSession = Depends(get_session)):
    now = datetime.now(timezone.utc)
    user = await session.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None:
        verify_password(body.password, DUMMY_HASH)
        raise HTTPException(401, {"code": "invalid_credentials"})

    if user.locked_until and user.locked_until > now:
        raise HTTPException(423, {"code": "locked", "locked_until": user.locked_until.isoformat()})
    if user.locked_until:
        user.failed_logins, user.locked_until = 0, None

    if not verify_password(body.password, user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= settings.max_failed_logins:
            user.locked_until = now + timedelta(minutes=settings.lock_minutes)
        await session.commit()
        if user.locked_until:
            raise HTTPException(423, {"code": "locked", "locked_until": user.locked_until.isoformat()})
        raise HTTPException(401, {"code": "invalid_credentials"})

    user.failed_logins = 0
    await session.commit()
    response.set_cookie(
        COOKIE_NAME, make_token(user.id, user.role.value), httponly=True, samesite="lax",
        secure=settings.cookie_secure, max_age=settings.session_hours * 3600, path="/",
    )
    return user_out(user)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return user_out(user)
