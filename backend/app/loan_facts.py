"""Loads what the scoring function needs from the database."""
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import IST, ist_day_start
from app.models import Loan, Outcome, OutcomeKind, Promise
from app.scoring import SCORING, LoanFacts, PromiseFact


async def load_facts(session: AsyncSession, loans: list[Loan], today: date) -> dict[str, LoanFacts]:
    ids = [loan.id for loan in loans]
    promises = defaultdict(list)
    for p in (await session.scalars(select(Promise).where(Promise.loan_id.in_(ids)))).all():
        promises[p.loan_id].append(PromiseFact(p.promised_date, p.status))

    since = ist_day_start(today - timedelta(days=SCORING["not_reachable"]["window_days"] - 1))
    unreachable = defaultdict(list)
    for loan_id, logged in (await session.execute(
        select(Outcome.loan_id, Outcome.logged_at_device).where(
            Outcome.loan_id.in_(ids), Outcome.kind == OutcomeKind.not_reachable, Outcome.logged_at_device >= since)
    )).all():
        unreachable[loan_id].append(logged.astimezone(IST).date())

    # a payment logged by an officer counts as a payment even before the next CSV import
    paid_logged = dict((await session.execute(
        select(Outcome.loan_id, func.max(Outcome.logged_at_device))
        .where(Outcome.loan_id.in_(ids), Outcome.kind == OutcomeKind.paid).group_by(Outcome.loan_id)
    )).all())

    return {
        loan.id: LoanFacts(
            loan_id=loan.id, outstanding=loan.outstanding, dpd=loan.dpd, status=loan.status,
            last_payment_date=latest(loan.last_payment_date, paid_logged.get(loan.id)),
            promises=tuple(promises[loan.id]), not_reachable_dates=tuple(unreachable[loan.id]),
        )
        for loan in loans
    }


def latest(imported: date | None, logged) -> date | None:
    logged_day = logged.astimezone(IST).date() if logged else None
    return max((d for d in (imported, logged_day) if d), default=None)
