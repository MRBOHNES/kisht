from datetime import date, datetime, timedelta

import pytest

from app.clock import IST
from app.models import Promise, PromiseStatus
from tests.world import PASSWORD, add, add_loan, reset_world

TODAY = date(2026, 11, 9)


@pytest.fixture(autouse=True)
async def world(set_now):
    ids = await reset_world()
    await add_loan("LN-1", ids["asha"], today=TODAY)
    await add_loan("LN-2", ids["bala"], today=TODAY)
    set_now(datetime(2026, 11, 9, 10, tzinfo=IST))
    return ids


def promise(days_from_today, status=PromiseStatus.open, loan_id="LN-1"):
    day = TODAY + timedelta(days=days_from_today)
    return Promise(loan_id=loan_id, officer_id=1, amount=5000, promised_date=day, status=status,
                   created_at=datetime.combine(day - timedelta(days=3), datetime.min.time(), IST))


async def get_promises(client, email="asha@t.in"):
    await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    return await client.get("/officer/promises")


async def test_promises_are_split_into_today_not_kept_and_upcoming(client):
    await add(promise(0), promise(2), promise(5), promise(-3, PromiseStatus.broken), promise(-1), promise(-4, PromiseStatus.kept))
    body = (await get_promises(client)).json()
    assert [p["promised_date"] for p in body["today"]] == ["2026-11-09"]
    assert [p["promised_date"] for p in body["upcoming"]] == ["2026-11-11", "2026-11-14"]
    # yesterday's open promise is broken on read; newest first
    assert [p["promised_date"] for p in body["not_kept"]] == ["2026-11-08", "2026-11-06"]


async def test_only_own_loans_promises_are_listed(client):
    await add(promise(1, loan_id="LN-2"))
    body = (await get_promises(client)).json()
    assert body["today"] == body["upcoming"] == body["not_kept"] == []


async def test_kept_rate_over_last_30_days(client):
    await add(promise(-1, PromiseStatus.kept), promise(-2, PromiseStatus.kept), promise(-3, PromiseStatus.broken),
              promise(-40, PromiseStatus.broken), promise(3))
    body = (await get_promises(client)).json()
    assert body["kept_rate"] == 0.67
    assert len(body["kept_rate_weeks"]) == 4 and body["kept_rate_weeks"][-1] == 0.67


async def test_kept_rate_is_null_without_due_promises(client):
    assert (await get_promises(client)).json()["kept_rate"] is None


async def test_promises_are_for_officers_only(client):
    assert (await get_promises(client, "manager@t.in")).status_code == 403
