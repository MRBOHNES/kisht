from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import ist_day_start, today_ist
from app.db import get_session
from app.deps import require_role
from app.loan_facts import load_facts
from app.models import Borrower, Loan, LoanStatus, Outcome, OutcomeKind, Promise, PromiseStatus, Role, User
from app.scoring import priority_list

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
