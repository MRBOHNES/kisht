from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import current_time
from app.db import get_session
from app.deps import require_role
from app.models import Outcome, Role, User
from app.outcomes import OutcomeIn, OutcomeRejected, record_outcome

router = APIRouter(prefix="/outcomes", tags=["outcomes"])


@router.post("")
async def log_outcome(
    body: OutcomeIn,
    session: AsyncSession = Depends(get_session),
    officer: User = Depends(require_role(Role.field_officer)),
    now: datetime = Depends(current_time),
):
    try:
        result = await record_outcome(session, officer, body, now)
        await session.commit()
    except OutcomeRejected as e:
        raise HTTPException(e.status, {"code": e.code, "message": e.message})
    except IntegrityError:
        # the same id arrived twice at the same moment; the other request stored it
        await session.rollback()
        existing = await session.get(Outcome, body.id)
        return {"id": str(body.id), "status": "duplicate", "out_of_window": existing.out_of_window_flag}
    return result
