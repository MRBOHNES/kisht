from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import IST, current_time, ist_date, ist_day_start
from app.db import get_session
from app.deps import require_role
from app.models import (
    Borrower, Branch, ContactAttempt, DpdSnapshot, Loan, LoanStatus, Outcome, PriorityOverride, Promise,
    PromiseStatus, Role, User,
)
from app.promises import mark_broken
from app.rollrate import ROLL_TARGET, roll_rates

router = APIRouter(prefix="/manager", tags=["manager"])
manager_only = require_role(Role.branch_manager)

SAME_DAY_TARGET = 0.95
WINDOW_DAYS = 30
UNTOUCHED_DAYS = 7
ABOUT_TO_ROLL_FROM = 25
LIST_LIMIT = 10


@router.get("/dashboard")
async def dashboard(
    session: AsyncSession = Depends(get_session),
    manager: User = Depends(manager_only),
    now: datetime = Depends(current_time),
):
    today = ist_date(now)
    await mark_broken(session, today)
    await session.commit()
    since = today - timedelta(days=WINDOW_DAYS - 1)

    branches = {b.id: b.name for b in (await session.scalars(select(Branch).order_by(Branch.name))).all()}
    snapshots = (await session.execute(
        select(DpdSnapshot.loan_id, DpdSnapshot.month, DpdSnapshot.dpd, Loan.branch_id)
        .join(Loan, Loan.id == DpdSnapshot.loan_id)
    )).all()
    roll = {
        "target": ROLL_TARGET,
        "all": roll_rates([(l, m, d) for l, m, d, _ in snapshots]),
        "branches": [
            {"branch": name, "steps": roll_rates([(l, m, d) for l, m, d, b in snapshots if b == branch_id])}
            for branch_id, name in branches.items()
        ],
    }

    broken = (await session.scalars(
        select(Promise.promised_date).where(Promise.status == PromiseStatus.broken, Promise.promised_date >= since)
    )).all()
    logged = (await session.execute(
        select(Outcome.logged_at_device, Outcome.synced_at).where(Outcome.logged_at_device >= ist_day_start(since))
    )).all()
    same_day = [ist_date(at) == ist_date(synced) for at, synced in logged]

    return {
        "date": today.isoformat(),
        "roll_rate": roll,
        "broken_promises": {"count": len(broken), "weeks": weekly(broken, today, lambda days: len(days))},
        "same_day": {
            "target": SAME_DAY_TARGET,
            "rate": round(sum(same_day) / len(same_day), 3) if same_day else None,
            "logged": len(same_day),
            "weeks": weekly([(ist_date(at), ist_date(at) == ist_date(s)) for at, s in logged], today, share_true),
        },
        "untouched": await untouched_count(session, now),
        "attention": {
            "about_to_roll": await about_to_roll(session),
            "not_kept": await recent_broken(session, today),
            "out_of_hours": await out_of_hours(session, since),
            "disputes": await disputes(session),
        },
        "pins": await current_pins(session),
    }


def weekly(items, today, summarise) -> list:
    """Four 7-day buckets, oldest first. Items are dates or (date, value) pairs."""
    out = []
    for w in (3, 2, 1, 0):
        end = today - timedelta(days=7 * w)
        start = end - timedelta(days=6)
        out.append(summarise([i for i in items if start <= (i[0] if isinstance(i, tuple) else i) <= end]))
    return out


def share_true(pairs) -> float | None:
    return round(sum(v for _, v in pairs) / len(pairs), 3) if pairs else None


async def untouched_count(session: AsyncSession, now: datetime) -> int:
    since = now - timedelta(days=UNTOUCHED_DAYS)
    touched_by_outcome = select(Outcome.loan_id).where(Outcome.logged_at_device >= since)
    touched_by_contact = select(ContactAttempt.loan_id).where(ContactAttempt.at >= since)
    return await session.scalar(
        select(func.count()).select_from(Loan).where(
            Loan.status == LoanStatus.active, Loan.id.not_in(touched_by_outcome), Loan.id.not_in(touched_by_contact))
    )


def loan_row(loan: Loan, borrower: Borrower, officer: User) -> dict:
    return {
        "loan_id": loan.id, "business_name": borrower.business_name, "business_type": borrower.business_type,
        "officer": officer.name, "dpd": loan.dpd, "outstanding": float(loan.outstanding),
    }


def loans_with_people():
    return (select(Loan, Borrower, User).join(Borrower, Borrower.id == Loan.borrower_id)
            .join(User, User.id == Loan.officer_id))


async def about_to_roll(session: AsyncSession) -> list[dict]:
    pinned = select(PriorityOverride.loan_id)
    rows = (await session.execute(
        loans_with_people().where(Loan.status == LoanStatus.active, Loan.dpd.between(ABOUT_TO_ROLL_FROM, 30),
                                  Loan.id.not_in(pinned))
        .order_by(Loan.outstanding.desc()).limit(LIST_LIMIT)
    )).all()
    return [loan_row(*r) for r in rows]


async def recent_broken(session: AsyncSession, today) -> list[dict]:
    rows = (await session.execute(
        select(Promise, Borrower, User).join(Loan, Loan.id == Promise.loan_id)
        .join(Borrower, Borrower.id == Loan.borrower_id).join(User, User.id == Loan.officer_id)
        .where(Promise.status == PromiseStatus.broken, Promise.promised_date >= today - timedelta(days=6))
        .order_by(Promise.promised_date.desc()).limit(LIST_LIMIT)
    )).all()
    return [{"loan_id": p.loan_id, "business_name": b.business_name, "business_type": b.business_type,
             "officer": u.name, "amount": float(p.amount), "promised_date": p.promised_date.isoformat()}
            for p, b, u in rows]


async def out_of_hours(session: AsyncSession, since) -> list[dict]:
    rows = (await session.execute(
        select(Outcome, User).join(User, User.id == Outcome.officer_id)
        .where(Outcome.out_of_window_flag.is_(True), Outcome.logged_at_device >= ist_day_start(since))
        .order_by(Outcome.logged_at_device.desc()).limit(LIST_LIMIT)
    )).all()
    return [{"loan_id": o.loan_id, "officer": u.name, "kind": o.kind.value,
             "logged_at": o.logged_at_device.astimezone(IST).isoformat()} for o, u in rows]


async def disputes(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(
        loans_with_people().where(Loan.status == LoanStatus.paused_dispute).order_by(Loan.dpd.desc())
    )).all()
    return [loan_row(*r) for r in rows]


async def current_pins(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(
        select(PriorityOverride, Loan, Borrower, User).join(Loan, Loan.id == PriorityOverride.loan_id)
        .join(Borrower, Borrower.id == Loan.borrower_id).join(User, User.id == Loan.officer_id)
        .where(PriorityOverride.officer_id == Loan.officer_id).order_by(PriorityOverride.created_at.desc())
    )).all()
    return [{**loan_row(loan, b, u), "reason": pin.reason} for pin, loan, b, u in rows]


class PinIn(BaseModel):
    loan_id: str = Field(max_length=20)
    reason: str = Field(min_length=3, max_length=200)


@router.post("/pins")
async def pin_loan(body: PinIn, session: AsyncSession = Depends(get_session), manager: User = Depends(manager_only)):
    """Puts a loan at the top of its officer's list. The score stays advisory; the pin is the manager's call."""
    loan = await session.get(Loan, body.loan_id)
    if loan is None:
        raise HTTPException(404, "loan not found")
    await session.execute(delete(PriorityOverride).where(PriorityOverride.loan_id == loan.id))
    session.add(PriorityOverride(loan_id=loan.id, officer_id=loan.officer_id, manager_id=manager.id,
                                 reason=body.reason.strip()))
    await session.commit()
    return {"loan_id": loan.id, "pinned": True}


@router.delete("/pins/{loan_id}")
async def unpin_loan(loan_id: str, session: AsyncSession = Depends(get_session), manager: User = Depends(manager_only)):
    await session.execute(delete(PriorityOverride).where(PriorityOverride.loan_id == loan_id))
    await session.commit()
    return {"loan_id": loan_id, "pinned": False}
