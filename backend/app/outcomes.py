"""Validates and records an officer's outcome. Shared by the online endpoint and offline sync."""
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import ist_date
from app.contact_window import in_contact_window
from app.models import Loan, LoanStatus, Outcome, OutcomeKind, Promise, PromiseStatus, User
from app.promises import mark_broken, mark_kept

MAX_AMOUNT = Decimal("9999999999.99")
PROMISE_MAX_DAYS = 30
# phone clocks drift a little; anything further ahead is a wrong clock
MAX_CLOCK_AHEAD = timedelta(minutes=5)
NEEDS_AMOUNT = {OutcomeKind.paid, OutcomeKind.promise}


class OutcomeIn(BaseModel):
    id: uuid.UUID  # generated on the phone
    loan_id: str = Field(max_length=20)
    kind: OutcomeKind
    amount: Decimal | None = Field(None, gt=0, le=MAX_AMOUNT, decimal_places=2)
    promise_date: date | None = None
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)
    logged_at_device: AwareDatetime


class OutcomeRejected(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def reject(code: str, message: str) -> None:
    raise OutcomeRejected(422, code, message)


def check_outcome(o: OutcomeIn, now: datetime) -> None:
    if o.kind in NEEDS_AMOUNT and o.amount is None:
        reject("amount_required", "An amount is needed for a payment or a promise")
    if o.kind not in NEEDS_AMOUNT and o.amount is not None:
        reject("amount_not_allowed", f"No amount is taken for '{o.kind.value}'")
    if o.kind == OutcomeKind.promise:
        # judged against the day it was logged, so an offline promise is not rejected for syncing late
        logged_day = ist_date(o.logged_at_device)
        if o.promise_date is None:
            reject("promise_date_required", "A promise needs a date")
        if o.promise_date < logged_day:
            reject("promise_date_past", "The promise date is in the past")
        if o.promise_date > logged_day + timedelta(days=PROMISE_MAX_DAYS):
            reject("promise_date_too_far", f"The promise date must be within {PROMISE_MAX_DAYS} days")
    elif o.promise_date is not None:
        reject("promise_date_not_allowed", "Only a promise has a promise date")
    if (o.lat is None) != (o.lng is None):
        reject("location_incomplete", "Send both latitude and longitude, or neither")
    if o.logged_at_device > now + MAX_CLOCK_AHEAD:
        reject("logged_in_future", "The phone's clock is ahead; check the date and time")


async def record_outcome(session: AsyncSession, officer: User, o: OutcomeIn, now: datetime) -> dict:
    """Adds the outcome to the session; the caller commits. A repeated id is ignored, not an error."""
    existing = await session.get(Outcome, o.id)
    if existing is not None:
        return {"id": str(o.id), "status": "duplicate", "out_of_window": existing.out_of_window_flag}

    loan = await session.get(Loan, o.loan_id)
    if loan is None or loan.officer_id != officer.id:
        raise OutcomeRejected(404, "loan_not_found", "Loan not found")
    check_outcome(o, now)

    outcome = Outcome(
        id=o.id, loan_id=loan.id, officer_id=officer.id, kind=o.kind, amount=o.amount,
        promise_date=o.promise_date, lat=o.lat, lng=o.lng, logged_at_device=o.logged_at_device,
        # stored either way; the manager sees flagged logs
        out_of_window_flag=not in_contact_window(o.logged_at_device),
    )
    if o.kind == OutcomeKind.promise:
        promise = Promise(loan_id=loan.id, officer_id=officer.id, amount=o.amount, promised_date=o.promise_date,
                          status=PromiseStatus.open, created_at=o.logged_at_device)
        session.add(promise)
        await session.flush()
        outcome.promise_id = promise.id
    elif o.kind == OutcomeKind.paid:
        await mark_kept(session, loan.id, o.logged_at_device)
    elif o.kind == OutcomeKind.dispute and loan.status == LoanStatus.active:
        loan.status = LoanStatus.paused_dispute
    session.add(outcome)
    await session.flush()
    await mark_broken(session, ist_date(now), [loan.id])
    return {"id": str(o.id), "status": "saved", "out_of_window": outcome.out_of_window_flag}
