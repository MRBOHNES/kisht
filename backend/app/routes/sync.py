from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import current_time
from app.db import get_session
from app.deps import require_role
from app.models import Role, User
from app.outcomes import OutcomeIn, OutcomeRejected, record_outcome

router = APIRouter(prefix="/sync", tags=["sync"])

MAX_BATCH = 100


class SyncIn(BaseModel):
    # items are validated one by one below, so one bad item doesn't reject the whole batch
    outcomes: list[dict] = Field(max_length=MAX_BATCH)


@router.post("")
async def sync_outcomes(
    body: SyncIn,
    session: AsyncSession = Depends(get_session),
    officer: User = Depends(require_role(Role.field_officer)),
    now: datetime = Depends(current_time),
):
    results = []
    for raw in body.outcomes:
        item_id = str(raw.get("id", ""))
        try:
            item = OutcomeIn.model_validate(raw)
        except ValidationError as e:
            first = e.errors()[0]
            field = ".".join(str(part) for part in first["loc"])
            results.append(rejected(item_id, "invalid", f"{field}: {first['msg']}"))
            continue
        try:
            # a savepoint per item: a rejected item leaves the others untouched
            async with session.begin_nested():
                results.append(await record_outcome(session, officer, item, now))
        except OutcomeRejected as e:
            results.append(rejected(item_id, e.code, e.message))
        except IntegrityError:
            results.append({"id": item_id, "status": "duplicate", "out_of_window": None})
    await session.commit()
    return {"results": results}


def rejected(item_id: str, code: str, message: str) -> dict:
    return {"id": item_id, "status": "rejected", "code": code, "message": message}
