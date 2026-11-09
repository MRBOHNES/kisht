import uuid
from datetime import date, datetime

import pytest
from sqlalchemy import func, select

from app.clock import IST
from app.db import SessionLocal
from app.models import Outcome
from tests.world import PASSWORD, add_loan, reset_world

TODAY = date(2026, 11, 9)


def ist(hour, minute=0, day=9):
    return datetime(2026, 11, day, hour, minute, tzinfo=IST)


@pytest.fixture(autouse=True)
async def world(set_now):
    ids = await reset_world()
    await add_loan("LN-1", ids["asha"], today=TODAY)
    await add_loan("LN-2", ids["bala"], today=TODAY)
    set_now(ist(21))
    return ids


@pytest.fixture
async def officer(client):
    await client.post("/auth/login", json={"email": "asha@t.in", "password": PASSWORD})
    return client


def item(kind="not_reachable", at=ist(10), **over):
    body = {"id": str(uuid.uuid4()), "loan_id": "LN-1", "kind": kind, "logged_at_device": at.isoformat()}
    if kind in ("paid", "promise"):
        body["amount"] = 5000
    if kind == "promise":
        body["promise_date"] = "2026-11-12"
    body.update(over)
    return body


async def sync(client, *items):
    response = await client.post("/sync", json={"outcomes": list(items)})
    return response


async def stored():
    async with SessionLocal() as s:
        return await s.scalar(select(func.count()).select_from(Outcome))


async def test_batch_is_saved_and_results_come_back_in_order(officer):
    a, b = item("paid"), item("promise")
    results = (await sync(officer, a, b)).json()["results"]
    assert [(r["id"], r["status"]) for r in results] == [(a["id"], "saved"), (b["id"], "saved")]
    assert await stored() == 2


async def test_resending_a_synced_item_is_ignored(officer):
    a = item()
    await sync(officer, a)
    results = (await sync(officer, a, item())).json()["results"]
    assert [r["status"] for r in results] == ["duplicate", "saved"]
    assert await stored() == 2


async def test_same_item_twice_in_one_batch_is_stored_once(officer):
    a = item()
    results = (await sync(officer, a, a)).json()["results"]
    assert [r["status"] for r in results] == ["saved", "duplicate"]
    assert await stored() == 1


async def test_contact_window_is_checked_against_the_phone_time_not_arrival(officer):
    # synced at 21:00 IST: the 10:00 log is fine, the 07:30 log is flagged but kept
    inside, outside = item(at=ist(10)), item(at=ist(7, 30))
    results = (await sync(officer, inside, outside)).json()["results"]
    assert [r["out_of_window"] for r in results] == [False, True]
    assert await stored() == 2


async def test_invalid_items_are_rejected_and_the_rest_saved(officer):
    good = item("paid")
    no_amount = item("paid", amount=None)
    bad_kind = item(kind="refund")
    past_promise = item("promise", promise_date="2026-11-01")
    results = (await sync(officer, no_amount, good, bad_kind, past_promise)).json()["results"]
    assert [r["status"] for r in results] == ["rejected", "saved", "rejected", "rejected"]
    assert [r.get("code") for r in results] == ["amount_required", None, "invalid", "promise_date_past"]
    assert all(r["message"] for r in results if r["status"] == "rejected")
    assert await stored() == 1


async def test_item_for_another_officers_loan_is_rejected(officer):
    results = (await sync(officer, item(loan_id="LN-2"), item())).json()["results"]
    assert [r["status"] for r in results] == ["rejected", "saved"]
    assert results[0]["code"] == "loan_not_found"
    assert await stored() == 1


async def test_item_without_a_usable_id_is_rejected(officer):
    results = (await sync(officer, item(id="not-a-uuid"), {"kind": "paid"})).json()["results"]
    assert [r["status"] for r in results] == ["rejected", "rejected"]


async def test_empty_batch_is_fine(officer):
    assert (await sync(officer)).json() == {"results": []}


async def test_batch_size_is_limited(officer):
    assert (await sync(officer, *[item() for _ in range(101)])).status_code == 422
    assert await stored() == 0


async def test_sync_is_for_officers_only(client):
    await client.post("/auth/login", json={"email": "manager@t.in", "password": PASSWORD})
    assert (await sync(client, item())).status_code == 403
    await client.post("/auth/logout")
    assert (await sync(client, item())).status_code == 401
