"""Deterministic sample data. Wipes every table, then reloads. Run: uv run python -m app.seed"""
import asyncio
import os
import random
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import bcrypt
from sqlalchemy import text

from app.assignment import pick_officer
from app.db import SessionLocal, engine
from app.models import (
    Borrower, Branch, CallLog, CallResult, ContactAttempt, ContactType, DpdSnapshot, Loan, LoanNote,
    LoanStatus, Message, MessageDirection, MessageStatus, NoteKind, Promise,
    PromiseStatus, Role, User,
)

ROLL_TARGET = 0.22
LOAN_COUNT = 300
IST = timezone(timedelta(hours=5, minutes=30))

BRANCHES = [
    ("Vijay Nagar", ["452010", "452011"]),
    ("Palasia", ["452001", "452018"]),
    ("Rajwada", ["452002", "452007"]),
]

# (name, email, branch index); first officer of each branch owns the brief rows
OFFICERS = [
    ("Rahul Chouhan", "officer@demo.in", 0),
    ("Neha Solanki", "neha@demo.in", 0),
    ("Vikram Patel", "vikram@demo.in", 0),
    ("Imran Qureshi", "imran@demo.in", 1),
    ("Pooja Jain", "pooja@demo.in", 1),
    ("Sandeep Yadav", "sandeep@demo.in", 1),
    ("Kavita Rathore", "kavita@demo.in", 2),
    ("Deepak Malviya", "deepak@demo.in", 2),
    ("Farah Sheikh", "farah@demo.in", 2),
    ("Mohit Dubey", "mohit@demo.in", 2),
]
MANAGERS = [
    ("Anita Sharma", "manager@demo.in", 0),
    ("Rohan Mehta", "manager2@demo.in", 1),
]

BUSINESS_TYPES = [
    "packaging_unit", "fertiliser_shop", "printing_press", "dairy_shop", "textile_shop",
    "hardware_store", "food_stall", "auto_parts", "stationery_shop", "tailoring_unit",
    "grocery_store", "electronics_repair",
]

# brief rows, exact: loan id, name, type, outstanding, dpd, officer email, promise
BRIEF_LOANS = [
    ("LN-10293", "Company B", "packaging_unit", 640000, 12, "officer@demo.in", (date(2026, 11, 5), "open")),
    ("LN-10871", "Company C", "fertiliser_shop", 310000, 27, "neha@demo.in", None),
    ("LN-11930", "Company D", "printing_press", 220000, 19, "imran@demo.in", (date(2026, 10, 31), "broken")),
]
NAMED_EXTRA = [
    ("Company E", "dairy_shop"), ("Company F", "textile_shop"), ("Company G", "hardware_store"),
    ("Company H", "food_stall"), ("Company I", "auto_parts"), ("Company J", "stationery_shop"),
    ("Company K", "tailoring_unit"),
]

BROKEN_REASONS = ["salary delayed", "stock not sold", "family emergency", "client payment stuck"]


def month_start(today: date, back: int) -> date:
    y, m = today.year, today.month - back
    while m < 1:
        y, m = y - 1, m + 12
    return date(y, m, 1)


def snapshots_for(loans: list[Loan], today: date, rng: random.Random) -> list[DpdSnapshot]:
    """Four monthly snapshots. Each month exactly ROLL_TARGET of loans in 1-30 roll past 30."""
    months = [month_start(today, back) for back in (4, 3, 2, 1)]
    state = {loan.id: rng.randint(1, 30) for loan in loans}
    rows = [DpdSnapshot(loan_id=i, month=months[0], dpd=d) for i, d in state.items()]
    for month in months[1:]:
        in_bucket = [i for i, d in state.items() if 1 <= d <= 30]
        rolling = set(rng.sample(in_bucket, round(len(in_bucket) * ROLL_TARGET)))
        for loan_id, dpd in state.items():
            state[loan_id] = rng.randint(31, 60) if loan_id in rolling else rng.randint(1, 30)
        rows += [DpdSnapshot(loan_id=i, month=month, dpd=d) for i, d in state.items()]
    return rows


async def seed(today: date | None = None) -> None:
    today = today or date.today()
    rng = random.Random(42)
    password = os.environ["SEED_PASSWORD"]
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    async with SessionLocal() as s:
        await s.execute(text("TRUNCATE branches, users, borrowers, loans, promises, outcomes, "
                             "contact_attempts, loan_notes, messages, call_logs, dpd_snapshots, "
                             "priority_overrides RESTART IDENTITY CASCADE"))
        branches = [Branch(name=n, pincodes=p) for n, p in BRANCHES]
        s.add_all(branches)
        await s.flush()

        officers = [User(name=n, email=e, password_hash=password_hash, role=Role.field_officer,
                         branch_id=branches[b].id) for n, e, b in OFFICERS]
        managers = [User(name=n, email=e, password_hash=password_hash, role=Role.branch_manager,
                         branch_id=branches[b].id) for n, e, b in MANAGERS]
        s.add_all(officers + managers)
        await s.flush()
        by_email = {u.email: u for u in officers + managers}
        load = {o.id: 0 for o in officers}

        specs = [(i, n, t, o, d, e, p) for i, n, t, o, d, e, p in BRIEF_LOANS]
        extra_ids = rng.sample(range(10000, 12999), LOAN_COUNT - len(BRIEF_LOANS))
        used = {sp[0] for sp in specs}
        extra_ids = [f"LN-{n}" for n in extra_ids if f"LN-{n}" not in used]
        for k in range(LOAN_COUNT - len(BRIEF_LOANS)):
            if k < len(NAMED_EXTRA):
                name, btype = NAMED_EXTRA[k]
            else:
                name, btype = f"Sample Trader {k:03d}", rng.choice(BUSINESS_TYPES)
            outstanding = rng.choice(range(40000, 900001, 5000))
            specs.append((extra_ids[k], name, btype, outstanding, rng.randint(1, 30), None, None))

        loans: list[Loan] = []
        disputed = set(rng.sample(range(len(BRIEF_LOANS), LOAN_COUNT), 6))
        for idx, (loan_id, name, btype, outstanding, dpd, officer_email, promise) in enumerate(specs):
            branch = branches[rng.randrange(3)]
            if officer_email:
                officer = by_email[officer_email]
                branch = next(b for b in branches if b.id == officer.branch_id)
            else:
                branch_officers = [o for o in officers if o.branch_id == branch.id]
                officer = pick_officer(branch_officers, load)
            load[officer.id] += 1

            borrower = Borrower(
                business_name=name, business_type=btype,
                phone="9" + "".join(str(rng.randint(0, 9)) for _ in range(9)),
                pincode=rng.choice(branch.pincodes),
                address=f"Sample address {rng.randint(1, 120)}, near market, Indore",
            )
            s.add(borrower)
            await s.flush()

            never_paid = idx >= len(BRIEF_LOANS) and rng.random() < 0.06
            last_paid = None if never_paid else today - timedelta(days=rng.randint(3, 75))
            loan = Loan(
                id=loan_id, borrower_id=borrower.id, branch_id=branch.id, officer_id=officer.id,
                outstanding=Decimal(outstanding), emi=Decimal(round(outstanding / 12, -2)),
                dpd=dpd, last_payment_date=last_paid,
                status=LoanStatus.paused_dispute if idx in disputed else LoanStatus.active,
            )
            s.add(loan)
            loans.append(loan)
            await s.flush()

            if promise:
                s.add(Promise(loan_id=loan_id, officer_id=officer.id, amount=loan.emi,
                              promised_date=promise[0], status=PromiseStatus(promise[1]),
                              broken_reason="salary delayed" if promise[1] == "broken" else None,
                              created_at=datetime.combine(promise[0] - timedelta(days=3), time(11), IST)))
            elif idx >= len(BRIEF_LOANS) and not never_paid:
                add_promise_history(s, loan, officer, today, rng)

        s.add_all(snapshots_for(loans, today, rng))
        await s.flush()
        add_demo_activity(s, by_email, today)
        await s.commit()


def add_promise_history(s, loan: Loan, officer: User, today: date, rng: random.Random) -> None:
    for _ in range(rng.choice([0, 0, 1, 1, 2, 3])):
        due = today - timedelta(days=rng.randint(4, 85))
        status = rng.choice([PromiseStatus.kept, PromiseStatus.broken])
        s.add(Promise(loan_id=loan.id, officer_id=officer.id, amount=loan.emi, promised_date=due,
                      status=status,
                      broken_reason=rng.choice(BROKEN_REASONS) if status == PromiseStatus.broken else None,
                      created_at=datetime.combine(due - timedelta(days=3), time(11), IST)))


def add_demo_activity(s, users: dict[str, User], today: date) -> None:
    rahul, neha, manager = users["officer@demo.in"], users["neha@demo.in"], users["manager@demo.in"]

    def at(days_ago: int, hour: int, minute: int = 0) -> datetime:
        return datetime.combine(today - timedelta(days=days_ago), time(hour, minute), IST)

    s.add_all([
        LoanNote(id=uuid.UUID(int=1), loan_id="LN-10293", author_id=rahul.id, author_role=Role.field_officer,
                 kind=NoteKind.note, text="Sample: owner was at the unit, said the buyer payment comes Tuesday.",
                 outcome_tag="promise", created_at=at(5, 12)),
        LoanNote(id=uuid.UUID(int=2), loan_id="LN-10871", author_id=manager.id, author_role=Role.branch_manager,
                 kind=NoteKind.instruction, text="Sample: visit this week, 27 days overdue. Ask for at least one EMI.",
                 created_at=at(1, 10)),
        LoanNote(id=uuid.UUID(int=3), loan_id="LN-10871", author_id=neha.id, author_role=Role.field_officer,
                 kind=NoteKind.note, text="Sample: shop closed on both visits, neighbour says owner is out of town.",
                 outcome_tag="not_reachable", created_at=at(2, 16)),
        Message(loan_id="LN-10871", officer_id=neha.id, template_key="reminder", direction=MessageDirection.out,
                rendered_text="Sample: Your EMI for LN-10871 is overdue. Please pay at the earliest.",
                status=MessageStatus.delivered, created_at=at(3, 11)),
        Message(loan_id="LN-10871", officer_id=neha.id, template_key=None, direction=MessageDirection.in_,
                rendered_text="Sample: I will pay after the harvest season, give me 10 days.",
                status=MessageStatus.read, created_at=at(3, 14)),
        Message(loan_id="LN-10871", officer_id=neha.id, template_key=None, direction=MessageDirection.out,
                rendered_text="Sample: Pay today or we will send police to your shop.",
                status=MessageStatus.blocked, blocked_reason="Threatening word: police",
                created_at=at(1, 9)),
        CallLog(loan_id="LN-10293", officer_id=rahul.id, started_at=at(5, 11, 30), duration_s=148,
                result=CallResult.connected, recording_url="/sample-audio/call-1.mp3",
                note="Sample: owner agreed to pay one EMI."),
        CallLog(loan_id="LN-10871", officer_id=neha.id, started_at=at(2, 10), duration_s=0,
                result=CallResult.no_answer, recording_url="/sample-audio/call-2.mp3", note=None),
        CallLog(loan_id="LN-10871", officer_id=neha.id, started_at=at(2, 15), duration_s=0,
                result=CallResult.switched_off, recording_url="/sample-audio/call-3.mp3", note=None),
        ContactAttempt(loan_id="LN-10871", officer_id=neha.id, type=ContactType.call, at=at(2, 10), allowed=True),
        ContactAttempt(loan_id="LN-10871", officer_id=neha.id, type=ContactType.visit, at=at(1, 7, 40), allowed=False,
                       blocked_reason="Outside contact hours 08:00-19:00 IST"),
    ])


async def main() -> None:
    await seed()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
