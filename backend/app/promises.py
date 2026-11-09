"""Promise status rules: a promise is kept by a payment on or before its date, broken once the date passes."""
from datetime import date, datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import ist_date
from app.models import Promise, PromiseStatus


async def mark_broken(session: AsyncSession, today: date, loan_ids: list[str] | None = None) -> None:
    """Open promises whose date has passed had no payment in time."""
    stmt = update(Promise).where(Promise.status == PromiseStatus.open, Promise.promised_date < today)
    if loan_ids is not None:
        stmt = stmt.where(Promise.loan_id.in_(loan_ids))
    await session.execute(stmt.values(status=PromiseStatus.broken))


async def mark_kept(session: AsyncSession, loan_id: str, paid_at: datetime) -> None:
    """A payment keeps every promise made before it that was due on or after the payment day.

    This includes promises already marked broken: a payment logged offline can reach the
    server after the promise date, but it still arrived in time.
    """
    await session.execute(
        update(Promise)
        .where(Promise.loan_id == loan_id, Promise.status != PromiseStatus.kept,
               Promise.created_at <= paid_at, Promise.promised_date >= ist_date(paid_at))
        .values(status=PromiseStatus.kept, broken_reason=None)
    )
