from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import current_time, ist_date, ist_day_start, today_ist
from app.db import get_session
from app.deps import require_role
from app.loan_facts import load_facts
from app.models import Borrower, Loan, LoanStatus, Outcome, OutcomeKind, Promise, PromiseStatus, Role, User
from app.promises import mark_broken
from app.scoring import SCORING, priority_list

router = APIRouter(prefix="/officer", tags=["officer"])


@router.get("/today")
async def today_list(
    session: AsyncSession = Depends(get_session),
    officer: User = Depends(require_role(Role.field_officer)),
):
    today = today_ist()
    rows = (await session.execute(
        select(Loan, Borrower).join(Borrower, Borrower.id == Loan.borrower_id)
        .where(Loan.officer_id == officer.id, Loan.status == LoanStatus.active)
    )).all()
    loans = {loan.id: (loan, borrower) for loan, borrower in rows}
    facts = await load_facts(session, [loan for loan, _ in rows], today)
    scores = priority_list(list(facts.values()), today)

    promises_today = await session.scalar(
        select(func.count()).select_from(Promise).join(Loan, Loan.id == Promise.loan_id).where(
            Loan.officer_id == officer.id, Loan.status == LoanStatus.active,
            Promise.status == PromiseStatus.open, Promise.promised_date == today)
    )
    collected_today = await session.scalar(
        select(func.coalesce(func.sum(Outcome.amount), 0)).where(
            Outcome.officer_id == officer.id, Outcome.kind == OutcomeKind.paid,
            Outcome.logged_at_device >= ist_day_start(today))
    )
    return {
        "officer_name": officer.name,
        "date": today.isoformat(),
        "kpis": {"list_count": len(scores), "promises_today": promises_today, "collected_today": float(collected_today)},
        "loans": [loan_card(rank, s, *loans[s.loan_id]) for rank, s in enumerate(scores, start=1)],
    }


def loan_card(rank: int, score, loan: Loan, borrower: Borrower) -> dict:
    return {
        "rank": rank,
        "loan_id": loan.id,
        "business_name": borrower.business_name,
        "business_type": borrower.business_type,
        "outstanding": float(loan.outstanding),
        "dpd": loan.dpd,
        "risk": score.risk,
        "priority": score.priority,
        "self_cure": score.self_cure,
        "low_confidence": score.low_confidence,
        "top_reason": score.reasons[0].__dict__ if score.reasons else None,
    }


KEPT_RATE_DAYS = 30


@router.get("/promises")
async def promises(
    session: AsyncSession = Depends(get_session),
    officer: User = Depends(require_role(Role.field_officer)),
    now: datetime = Depends(current_time),
):
    today = ist_date(now)
    loan_ids = list((await session.scalars(select(Loan.id).where(Loan.officer_id == officer.id))).all())
    await mark_broken(session, today, loan_ids)
    await session.commit()

    since = today - timedelta(days=SCORING["broken_promises"]["window_days"])
    rows = (await session.execute(
        select(Promise, Borrower).join(Loan, Loan.id == Promise.loan_id).join(Borrower, Borrower.id == Loan.borrower_id)
        .where(Loan.officer_id == officer.id, Promise.promised_date >= since)
        .order_by(Promise.promised_date, Promise.id)
    )).all()

    def pick(keep):
        return [promise_card(p, b) for p, b in rows if keep(p)]

    return {
        "date": today.isoformat(),
        "kept_rate": kept_rate([p for p, _ in rows], today - timedelta(days=KEPT_RATE_DAYS - 1), today),
        "kept_rate_weeks": [
            kept_rate([p for p, _ in rows], today - timedelta(days=7 * w + 6), today - timedelta(days=7 * w))
            for w in (3, 2, 1, 0)
        ],
        "today": pick(lambda p: p.status == PromiseStatus.open and p.promised_date == today),
        "not_kept": list(reversed(pick(lambda p: p.status == PromiseStatus.broken))),
        "upcoming": pick(lambda p: p.status == PromiseStatus.open and p.promised_date > today),
    }


def kept_rate(promises: list[Promise], start, end) -> float | None:
    """Share of promises falling due in [start, end] that were kept; None when none were due."""
    done = [p for p in promises if start <= p.promised_date <= end and p.status != PromiseStatus.open]
    return round(sum(p.status == PromiseStatus.kept for p in done) / len(done), 2) if done else None


def promise_card(p: Promise, borrower: Borrower) -> dict:
    return {
        "id": p.id, "loan_id": p.loan_id, "business_name": borrower.business_name,
        "business_type": borrower.business_type, "amount": float(p.amount),
        "promised_date": p.promised_date.isoformat(), "status": p.status.value,
    }
