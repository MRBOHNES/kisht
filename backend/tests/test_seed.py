from datetime import date

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import DpdSnapshot, Loan, User
from app.seed import seed

TODAY = date(2026, 11, 9)


async def loan_rows():
    async with SessionLocal() as s:
        result = await s.execute(select(Loan.id, Loan.outstanding, Loan.dpd, Loan.officer_id).order_by(Loan.id))
        return result.all()


async def test_seed_is_deterministic():
    await seed(TODAY)
    first = await loan_rows()
    await seed(TODAY)
    assert await loan_rows() == first


async def test_brief_rows_are_exact():
    await seed(TODAY)
    async with SessionLocal() as s:
        rows = {}
        for loan_id in ("LN-10293", "LN-10871", "LN-11930"):
            loan = await s.get(Loan, loan_id)
            officer = await s.get(User, loan.officer_id)
            rows[loan_id] = (int(loan.outstanding), loan.dpd, officer.name)
    assert rows == {
        "LN-10293": (640000, 12, "Rahul Chouhan"),
        "LN-10871": (310000, 27, "Neha Solanki"),
        "LN-11930": (220000, 19, "Imran Qureshi"),
    }


async def test_seeded_roll_rate_is_about_22_percent():
    await seed(TODAY)
    async with SessionLocal() as s:
        snaps = (await s.execute(select(DpdSnapshot))).scalars().all()
    by_month = {}
    for snap in snaps:
        by_month.setdefault(snap.month, {})[snap.loan_id] = snap.dpd
    months = sorted(by_month)
    assert len(months) == 4
    start = rolled = 0
    for prev, nxt in zip(months, months[1:]):
        for loan_id, dpd in by_month[prev].items():
            if 1 <= dpd <= 30:
                start += 1
                rolled += by_month[nxt][loan_id] > 30
    assert 0.20 <= rolled / start <= 0.24


async def test_seed_counts():
    await seed(TODAY)
    async with SessionLocal() as s:
        loans = await s.scalar(select(func.count()).select_from(Loan))
        users = await s.scalar(select(func.count()).select_from(User))
    assert loans == 300
    assert users == 12
