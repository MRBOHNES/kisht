from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Role, User
from app.security import COOKIE_NAME, read_token


async def current_user(request: Request, session: AsyncSession = Depends(get_session)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    claims = read_token(token) if token else None
    # role is read from the database, not the token, so a role change takes effect at once
    user = await session.get(User, int(claims["sub"])) if claims else None
    if user is None:
        raise HTTPException(401, "not signed in")
    return user


def require_role(role: Role):
    async def check(user: User = Depends(current_user)) -> User:
        if user.role != role:
            raise HTTPException(403, "this action is not allowed for your role")
        return user

    return check
