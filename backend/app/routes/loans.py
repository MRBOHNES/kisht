from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clock import today_ist
from app.db import get_session
from app.deps import current_user
from app.loan_facts import load_facts
from app.models import Borrower, ContactAttempt, Loan, Role, User
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
        "contact_attempts": [
            {"type": a.type.value, "at": a.at.isoformat(), "allowed": a.allowed, "blocked_reason": a.blocked_reason}
            for a in attempts
        ],
    }


def mask_phone(phone: str) -> str:
    return "•" * (len(phone) - 4) + phone[-4:]
