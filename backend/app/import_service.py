from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.assignment import pick_officer
from app.csv_import import ParseResult
from app.models import Borrower, Branch, Loan, LoanStatus, Role, User


@dataclass
class ImportSummary:
    created: int = 0
    updated: int = 0
    cured: int = 0
    new_by_officer: dict[int, int] = field(default_factory=lambda: defaultdict(int))


async def run_import(session: AsyncSession, parsed: ParseResult, branches: list[Branch]) -> ImportSummary:
    summary = ImportSummary()
    branch_of_pincode = {p: b for b in branches for p in b.pincodes}
    officers = (await session.scalars(select(User).where(User.role == Role.field_officer))).all()
    officers_by_branch: dict[int, list[User]] = defaultdict(list)
    for officer in officers:
        officers_by_branch[officer.branch_id].append(officer)

    open_loans = dict((await session.execute(
        select(Loan.officer_id, func.count()).where(Loan.status != LoanStatus.cured).group_by(Loan.officer_id)
    )).all())

    ids = [row.loan_id for row in parsed.valid]
    existing = {l.id: l for l in (await session.scalars(select(Loan).where(Loan.id.in_(ids)))).all()}

    for row in parsed.valid:
        loan = existing.get(row.loan_id)
        if loan:
            if loan.status == LoanStatus.cured:
                loan.status = LoanStatus.active
                open_loans[loan.officer_id] = open_loans.get(loan.officer_id, 0) + 1
            loan.outstanding, loan.emi, loan.dpd = row.outstanding, row.emi, row.dpd
            loan.last_payment_date = row.last_payment_date
            summary.updated += 1
            continue

        branch = branch_of_pincode[row.pincode]
        officer = pick_officer(officers_by_branch[branch.id], open_loans)
        borrower = Borrower(
            business_name=row.business_name, business_type=row.business_type,
            phone=row.phone, pincode=row.pincode, address=row.address,
        )
        session.add(borrower)
        await session.flush()
        session.add(Loan(
            id=row.loan_id, borrower_id=borrower.id, branch_id=branch.id, officer_id=officer.id,
            outstanding=row.outstanding, emi=row.emi, dpd=row.dpd,
            last_payment_date=row.last_payment_date, status=LoanStatus.active,
        ))
        open_loans[officer.id] = open_loans.get(officer.id, 0) + 1
        summary.new_by_officer[officer.id] += 1
        summary.created += 1

    # a file with no usable rows is a wrong file, not "nothing is overdue today"
    if parsed.valid:
        cured = await session.execute(
            update(Loan).where(Loan.status != LoanStatus.cured, Loan.id.not_in(parsed.seen_ids))
            .values(status=LoanStatus.cured)
        )
        summary.cured = cured.rowcount
    await session.flush()
    return summary


async def assignment_table(session: AsyncSession, new_by_officer: dict[int, int]) -> list[dict]:
    rows = (await session.execute(
        select(
            User.id, User.name, Branch.name,
            func.count(Loan.id), func.array_agg(func.distinct(Borrower.pincode)),
        )
        .join(Branch, Branch.id == User.branch_id)
        .outerjoin(Loan, (Loan.officer_id == User.id) & (Loan.status != LoanStatus.cured))
        .outerjoin(Borrower, Borrower.id == Loan.borrower_id)
        .where(User.role == Role.field_officer)
        .group_by(User.id, User.name, Branch.name)
        .order_by(Branch.name, User.name)
    )).all()
    return [
        {
            "officer_id": uid, "officer_name": name, "branch": branch,
            "pincodes": sorted(p for p in pins if p), "open_loans": count,
            "new_in_import": new_by_officer.get(uid, 0),
        }
        for uid, name, branch, count, pins in rows
    ]
