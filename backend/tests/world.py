"""Small fixed data set for tests that must not depend on the 300-loan seed."""
from datetime import datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import text

from app.clock import IST, today_ist
from app.db import SessionLocal
from app.models import Borrower, Branch, Loan, LoanStatus, Role, User
from app.security import hash_password

PASSWORD = "correct-horse"
PINCODE_A, PINCODE_B = "452010", "452001"

_hash = hash_password(PASSWORD)


async def reset_world() -> dict:
    async with SessionLocal() as s:
        await s.execute(text(
            "TRUNCATE branches, users, borrowers, loans, promises, outcomes, contact_attempts, "
            "loan_notes, messages, call_logs, dpd_snapshots, priority_overrides RESTART IDENTITY CASCADE"
        ))
        a = Branch(name="Branch A", pincodes=[PINCODE_A])
        b = Branch(name="Branch B", pincodes=[PINCODE_B])
        s.add_all([a, b])
        await s.flush()

        def user(name, email, role, branch):
            return User(name=name, email=email, password_hash=_hash, role=role, branch_id=branch.id)

        users = {
            "asha": user("Asha", "asha@t.in", Role.field_officer, a),
            "bala": user("Bala", "bala@t.in", Role.field_officer, a),
            "chitra": user("Chitra", "chitra@t.in", Role.field_officer, b),
            "manager": user("Manager", "manager@t.in", Role.branch_manager, a),
        }
        s.add_all(users.values())
        await s.commit()
        return {k: u.id for k, u in users.items()}



def csv_text(*rows: str) -> str:
    header = "loan_id,business_name,business_type,phone,pincode,outstanding,emi,dpd,last_payment_date,address"
    return "\n".join([header, *rows]) + "\n"


def good_row(loan_id="LN-1", pincode=PINCODE_A, dpd="12", **over) -> str:
    cells = {
        "loan_id": loan_id, "name": "Shop", "type": "dairy_shop", "phone": "9876543210",
        "pincode": pincode, "outstanding": "100000", "emi": "9000", "dpd": dpd,
        "last": "2026-10-20", "address": "",
    }
    cells.update(over)
    return ",".join(cells.values())


async def add_loan(loan_id, officer_id, dpd=12, outstanding=200_000, paid_days_ago=20,
                   status=LoanStatus.active, phone="9876543210", today=None):
    today = today or today_ist()
    async with SessionLocal() as s:
        borrower = Borrower(business_name=f"Shop {loan_id}", business_type="dairy_shop", phone=phone,
                            pincode=PINCODE_A, address="Sample address")
        s.add(borrower)
        await s.flush()
        s.add(Loan(id=loan_id, borrower_id=borrower.id, branch_id=1, officer_id=officer_id,
                   outstanding=Decimal(outstanding), emi=Decimal(10_000), dpd=dpd, status=status,
                   last_payment_date=None if paid_days_ago is None else today - timedelta(days=paid_days_ago)))
        await s.commit()


async def add(*rows):
    async with SessionLocal() as s:
        s.add_all(rows)
        await s.commit()


def at_today(hour: int, minute: int = 0) -> datetime:
    return datetime.combine(today_ist(), time(hour, minute), IST)
