from datetime import date, datetime, timedelta

import pytest

from app.clock import IST
from app.models import DpdSnapshot, LoanStatus, Promise, PromiseStatus
from tests.world import PASSWORD, add, add_loan, reset_world

TODAY = date(2026, 11, 9)


@pytest.fixture(autouse=True)
async def world(set_now):
    ids = await reset_world()
    await add_loan("LN-1", ids["asha"], dpd=27, outstanding=500_000, today=TODAY)
    await add_loan("LN-2", ids["asha"], dpd=3, outstanding=50_000, paid_days_ago=2, today=TODAY)
    await add_loan("LN-3", ids["chitra"], dpd=12, status=LoanStatus.paused_dispute, today=TODAY)
    set_now(datetime(2026, 11, 9, 10, tzinfo=IST))
    return ids


async def login(client, email):
    await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    return client


async def test_dashboard_reports_roll_rate_by_branch_against_target(client):
    sep, octo = date(2026, 9, 1), date(2026, 10, 1)
    await add(DpdSnapshot(loan_id="LN-1", month=sep, dpd=20), DpdSnapshot(loan_id="LN-1", month=octo, dpd=35),
              DpdSnapshot(loan_id="LN-2", month=sep, dpd=10), DpdSnapshot(loan_id="LN-2", month=octo, dpd=12))
    roll = (await (await login(client, "manager@t.in")).get("/manager/dashboard")).json()["roll_rate"]
    assert roll["target"] == 0.16
    assert roll["all"][0]["rate"] == 0.5
    branch_a = next(b for b in roll["branches"] if b["branch"] == "Branch A")
    assert branch_a["steps"][0]["rate"] == 0.5


async def test_dashboard_lists_disputes_and_loans_about_to_roll(client):
    body = (await (await login(client, "manager@t.in")).get("/manager/dashboard")).json()
    assert [d["loan_id"] for d in body["attention"]["disputes"]] == ["LN-3"]
    assert [d["loan_id"] for d in body["attention"]["about_to_roll"]] == ["LN-1"]
    assert body["untouched"] == 2


async def test_dashboard_counts_broken_promises_in_last_30_days(client):
    await add(Promise(loan_id="LN-1", officer_id=1, amount=1000, promised_date=TODAY - timedelta(days=3),
                      status=PromiseStatus.open, created_at=datetime(2026, 11, 1, tzinfo=IST)),
              Promise(loan_id="LN-1", officer_id=1, amount=1000, promised_date=TODAY - timedelta(days=40),
                      status=PromiseStatus.broken, created_at=datetime(2026, 9, 1, tzinfo=IST)))
    body = (await (await login(client, "manager@t.in")).get("/manager/dashboard")).json()
    assert body["broken_promises"]["count"] == 1
    assert body["attention"]["not_kept"][0]["loan_id"] == "LN-1"


async def test_dashboard_is_for_managers_only(client):
    assert (await (await login(client, "asha@t.in")).get("/manager/dashboard")).status_code == 403


async def test_pinned_loan_goes_to_the_top_of_the_officers_list(client):
    await login(client, "manager@t.in")
    assert (await client.post("/manager/pins", json={"loan_id": "LN-2", "reason": "Owner leaving town"})).status_code == 200
    await client.post("/auth/logout")
    cards = (await (await login(client, "asha@t.in")).get("/officer/today")).json()["loans"]
    assert [(c["loan_id"], c["pinned"]) for c in cards] == [("LN-2", True), ("LN-1", False)]
    assert cards[0]["pin_reason"] == "Owner leaving town" and cards[0]["rank"] == 1


async def test_only_managers_can_pin(client):
    response = await (await login(client, "asha@t.in")).post("/manager/pins", json={"loan_id": "LN-2", "reason": "mine first"})
    assert response.status_code == 403
    cards = (await client.get("/officer/today")).json()["loans"]
    assert not any(c["pinned"] for c in cards)


async def test_pin_needs_a_reason_and_a_real_loan(client):
    await login(client, "manager@t.in")
    assert (await client.post("/manager/pins", json={"loan_id": "LN-2", "reason": ""})).status_code == 422
    assert (await client.post("/manager/pins", json={"loan_id": "LN-99", "reason": "check"})).status_code == 404


async def test_unpin_restores_score_order(client):
    await login(client, "manager@t.in")
    await client.post("/manager/pins", json={"loan_id": "LN-2", "reason": "Owner leaving town"})
    await client.delete("/manager/pins/LN-2")
    pins = (await client.get("/manager/dashboard")).json()["pins"]
    assert pins == []
    await client.post("/auth/logout")
    cards = (await (await login(client, "asha@t.in")).get("/officer/today")).json()["loans"]
    assert cards[0]["loan_id"] == "LN-1"


async def test_pin_for_previous_officer_does_not_follow_the_loan(client, world):
    from app.db import SessionLocal
    from app.models import Loan
    await login(client, "manager@t.in")
    await client.post("/manager/pins", json={"loan_id": "LN-2", "reason": "Owner leaving town"})
    async with SessionLocal() as s:
        (await s.get(Loan, "LN-2")).officer_id = world["bala"]
        await s.commit()
    await client.post("/auth/logout")
    cards = (await (await login(client, "bala@t.in")).get("/officer/today")).json()["loans"]
    assert cards[0]["pinned"] is False
