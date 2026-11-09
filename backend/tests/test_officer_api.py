import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest

from app.clock import IST, today_ist
from app.db import SessionLocal
from app.models import (
    Borrower, ContactAttempt, ContactType, Loan, LoanStatus, Outcome, OutcomeKind, Promise, PromiseStatus,
)
from tests.world import PASSWORD, PINCODE_A, reset_world


@pytest.fixture(autouse=True)
async def world():
    return await reset_world()


async def add_loan(loan_id, officer_id, dpd=12, outstanding=200_000, paid_days_ago=20,
                   status=LoanStatus.active, phone="9876543210"):
    today = today_ist()
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


def at_today(hour: int) -> datetime:
    return datetime.combine(today_ist(), time(hour), IST)


async def login(client, email):
    await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    return client


async def test_today_lists_only_own_active_loans_by_priority(client, world):
    await add_loan("LN-1", world["asha"], dpd=5)
    await add_loan("LN-2", world["asha"], dpd=28)
    await add_loan("LN-3", world["bala"], dpd=29)
    await add_loan("LN-4", world["asha"], dpd=29, status=LoanStatus.paused_dispute)
    await add_loan("LN-5", world["asha"], dpd=29, status=LoanStatus.cured)
    body = (await (await login(client, "asha@t.in")).get("/officer/today")).json()
    assert [(c["rank"], c["loan_id"]) for c in body["loans"]] == [(1, "LN-2"), (2, "LN-1")]
    assert body["loans"][0]["top_reason"]["key"] == "roll_risk"
    assert body["loans"][0]["top_reason"]["text_hi"]
    assert body["kpis"]["list_count"] == 2


async def test_today_is_for_officers_only(client):
    await login(client, "manager@t.in")
    assert (await client.get("/officer/today")).status_code == 403


async def test_today_requires_login(client):
    assert (await client.get("/officer/today")).status_code == 401


async def test_kpis_count_promises_due_today_and_cash_collected_today(client, world):
    await add_loan("LN-1", world["asha"])
    await add(
        Promise(loan_id="LN-1", officer_id=world["asha"], amount=5000, promised_date=today_ist(),
                status=PromiseStatus.open),
        Outcome(id=uuid.uuid4(), loan_id="LN-1", officer_id=world["asha"], kind=OutcomeKind.paid,
                amount=Decimal(7500), logged_at_device=at_today(10)),
    )
    kpis = (await (await login(client, "asha@t.in")).get("/officer/today")).json()["kpis"]
    assert kpis["promises_today"] == 1 and kpis["collected_today"] == 7500


async def test_not_reachable_logs_raise_the_score(client, world):
    await add_loan("LN-1", world["asha"], dpd=12, paid_days_ago=3)
    await login(client, "asha@t.in")
    before = (await client.get("/officer/today")).json()["loans"][0]["risk"]
    await add(*[Outcome(id=uuid.uuid4(), loan_id="LN-1", officer_id=world["asha"],
                        kind=OutcomeKind.not_reachable, logged_at_device=at_today(9 + i)) for i in range(3)])
    after = (await client.get("/officer/today")).json()["loans"][0]["risk"]
    assert after == before + 10


async def test_logged_payment_counts_as_recent_payment(client, world):
    await add_loan("LN-1", world["asha"], dpd=12, paid_days_ago=40)
    await add(Outcome(id=uuid.uuid4(), loan_id="LN-1", officer_id=world["asha"], kind=OutcomeKind.paid,
                      amount=Decimal(10_000), logged_at_device=at_today(10)))
    card = (await (await login(client, "asha@t.in")).get("/officer/today")).json()["loans"][0]
    assert card["self_cure"] == "paid_recently"


async def test_officer_can_read_own_loan(client, world):
    await add_loan("LN-1", world["asha"], phone="9876543210")
    body = (await (await login(client, "asha@t.in")).get("/loans/LN-1")).json()
    assert body["phone_masked"] == "••••••3210"
    assert "9876543210" not in str(body)
    assert len(body["score"]["reasons"]) >= 1


async def test_officer_cannot_read_another_officers_loan(client, world):
    await add_loan("LN-1", world["bala"])
    response = await (await login(client, "asha@t.in")).get("/loans/LN-1")
    assert response.status_code == 404
    assert "Shop" not in response.text


async def test_unknown_and_foreign_loans_look_the_same(client, world):
    await add_loan("LN-1", world["bala"])
    await login(client, "asha@t.in")
    foreign, missing = await client.get("/loans/LN-1"), await client.get("/loans/LN-999")
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json()


async def test_manager_can_read_any_loan(client, world):
    await add_loan("LN-1", world["chitra"])
    assert (await (await login(client, "manager@t.in")).get("/loans/LN-1")).status_code == 200


async def test_detail_lists_contact_attempts_including_blocked(client, world):
    await add_loan("LN-1", world["asha"])
    await add(
        ContactAttempt(loan_id="LN-1", officer_id=world["asha"], type=ContactType.call, at=at_today(10), allowed=True),
        ContactAttempt(loan_id="LN-1", officer_id=world["asha"], type=ContactType.visit, at=at_today(7),
                       allowed=False, blocked_reason="Outside contact hours"),
    )
    attempts = (await (await login(client, "asha@t.in")).get("/loans/LN-1")).json()["contact_attempts"]
    assert [(a["type"], a["allowed"]) for a in attempts] == [("call", True), ("visit", False)]
    assert attempts[1]["blocked_reason"] == "Outside contact hours"


async def test_loan_detail_requires_login(client, world):
    await add_loan("LN-1", world["asha"])
    assert (await client.get("/loans/LN-1")).status_code == 401
