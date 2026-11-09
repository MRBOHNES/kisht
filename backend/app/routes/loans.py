from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import current_time, today_ist
from app.contact_window import BLOCKED_REASON, in_contact_window
from app.db import get_session
from app.deps import current_user, require_role
from app.loan_facts import load_facts
from app.models import Borrower, ContactAttempt, ContactType, Loan, Role, User
from app.scoring import score_loan

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("/{loan_id}")
async def loan_detail(
    loan_id: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
):
    loan = await session.get(Loan, loan_id)
    # 404 rather than 403 so an officer can't probe which loan ids exist
    if loan is None or (user.role == Role.field_officer and loan.officer_id != user.id):
        raise HTTPException(404, "loan not found")
    borrower = await session.get(Borrower, loan.borrower_id)
    today = today_ist()
    score = score_loan((await load_facts(session, [loan], today))[loan.id], today)
    attempts = (await session.scalars(
        select(ContactAttempt).where(ContactAttempt.loan_id == loan.id).order_by(ContactAttempt.at.desc())
    )).all()
    return {
        "loan_id": loan.id,
        "status": loan.status.value,
        "business_name": borrower.business_name,
        "business_type": borrower.business_type,
        "phone_masked": mask_phone(borrower.phone),
        "address": borrower.address,
        "pincode": borrower.pincode,
        "outstanding": float(loan.outstanding),
        "emi": float(loan.emi),
        "dpd": loan.dpd,
        "last_payment_date": loan.last_payment_date.isoformat() if loan.last_payment_date else None,
        "score": {
            "risk": score.risk, "priority": score.priority, "amount_factor": score.amount_factor,
            "self_cure": score.self_cure, "low_confidence": score.low_confidence,
            "reasons": [r.__dict__ for r in score.reasons],
        },
        "contact_attempts": [attempt_out(a) for a in attempts],
    }


class ContactIn(BaseModel):
    type: ContactType


@router.post("/{loan_id}/contact")
async def contact_borrower(
    loan_id: str,
    body: ContactIn,
    session: AsyncSession = Depends(get_session),
    officer: User = Depends(require_role(Role.field_officer)),
    now: datetime = Depends(current_time),
):
    """Every call or visit attempt is stored; outside the contact window it is blocked."""
    loan = await session.get(Loan, loan_id)
    if loan is None or loan.officer_id != officer.id:
        raise HTTPException(404, "loan not found")
    allowed = in_contact_window(now)
    attempt = ContactAttempt(loan_id=loan.id, officer_id=officer.id, type=body.type, at=now, allowed=allowed,
                             blocked_reason=None if allowed else BLOCKED_REASON)
    session.add(attempt)
    await session.commit()
    if not allowed:
        raise HTTPException(403, {"code": "outside_contact_hours", "message": BLOCKED_REASON,
                                  "attempt": attempt_out(attempt)})
    # the full number is only handed out for a call that is allowed right now
    borrower = await session.get(Borrower, loan.borrower_id)
    phone = borrower.phone if body.type == ContactType.call else None
    return {"allowed": True, "attempt": attempt_out(attempt), "phone": phone}


def attempt_out(a: ContactAttempt) -> dict:
    return {"type": a.type.value, "at": a.at.isoformat(), "allowed": a.allowed, "blocked_reason": a.blocked_reason}


def mask_phone(phone: str) -> str:
    return "•" * (len(phone) - 4) + phone[-4:]
