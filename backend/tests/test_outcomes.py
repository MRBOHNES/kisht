import uuid
from datetime import date, datetime

import pytest
from sqlalchemy import func, select

from app.clock import IST
from app.db import SessionLocal
from app.models import Loan, LoanStatus, Outcome, Promise, PromiseStatus
from tests.world import PASSWORD, add, add_loan, reset_world

TODAY = date(2026, 11, 9)


def ist(hour, minute=0, day=9):
    return datetime(2026, 11, day, hour, minute, tzinfo=IST)


@pytest.fixture(autouse=True)
async def world(set_now):
    ids = await reset_world()
    await add_loan("LN-1", ids["asha"], today=TODAY)
    await add_loan("LN-2", ids["bala"], today=TODAY)
    set_now(ist(10))
    return ids


@pytest.fixture
async def officer(client):
    await client.post("/auth/login", json={"email": "asha@t.in", "password": PASSWORD})
    return client


def payload(kind="paid", **over):
    body = {"id": str(uuid.uuid4()), "loan_id": "LN-1", "kind": kind, "logged_at_device": ist(10).isoformat()}
    if kind in ("paid", "promise"):
        body["amount"] = 10000
    if kind == "promise":
        body["promise_date"] = "2026-11-12"
    body.update(over)
    return body


async def post(client, body):
    return await client.post("/outcomes", json=body)


async def count(model):
    async with SessionLocal() as s:
        return await s.scalar(select(func.count()).select_from(model))


async def test_paid_outcome_is_saved(officer):
    response = await post(officer, payload())
    assert response.json() == {"id": response.json()["id"], "status": "saved", "out_of_window": False}
    assert await count(Outcome) == 1


async def test_location_is_optional_and_stored(officer):
    body = payload(lat=22.72, lng=75.86)
    await post(officer, body)
    async with SessionLocal() as s:
        stored = await s.get(Outcome, uuid.UUID(body["id"]))
    assert (stored.lat, stored.lng) == (22.72, 75.86)
    assert (await post(officer, payload(lat=None, lng=None))).status_code == 200


async def test_outcome_logged_outside_contact_hours_is_stored_and_flagged(officer, set_now):
    set_now(ist(20))
    response = await post(officer, payload("not_reachable", logged_at_device=ist(19, 30).isoformat()))
    assert response.status_code == 200 and response.json()["out_of_window"] is True
    assert await count(Outcome) == 1


async def test_promise_outcome_creates_open_promise(officer):
    body = payload("promise", amount=20000, promise_date="2026-11-12")
    await post(officer, body)
    async with SessionLocal() as s:
        promise = (await s.scalars(select(Promise))).one()
        outcome = await s.get(Outcome, uuid.UUID(body["id"]))
    assert (promise.status, promise.promised_date, int(promise.amount)) == (PromiseStatus.open, date(2026, 11, 12), 20000)
    assert outcome.promise_id == promise.id


async def test_paid_marks_open_promise_kept(officer, set_now):
    await post(officer, payload("promise", promise_date="2026-11-10"))
    set_now(ist(12))
    assert (await post(officer, payload("paid", logged_at_device=ist(11).isoformat()))).status_code == 200
    async with SessionLocal() as s:
        assert (await s.scalars(select(Promise))).one().status == PromiseStatus.kept


async def test_promise_past_its_date_without_payment_is_broken(officer, set_now):
    await post(officer, payload("promise", promise_date="2026-11-10"))
    set_now(ist(10, day=12))
    await post(officer, payload("not_reachable", logged_at_device=ist(10, day=12).isoformat()))
    async with SessionLocal() as s:
        assert (await s.scalars(select(Promise))).one().status == PromiseStatus.broken


async def test_dispute_pauses_the_loan_and_drops_it_from_today(officer):
    await post(officer, payload("dispute"))
    async with SessionLocal() as s:
        assert (await s.get(Loan, "LN-1")).status == LoanStatus.paused_dispute
    assert (await officer.get("/officer/today")).json()["loans"] == []


async def test_repeated_id_is_ignored_not_an_error(officer):
    body = payload()
    first, second = await post(officer, body), await post(officer, body)
    assert first.json()["status"] == "saved" and second.json()["status"] == "duplicate"
    assert second.status_code == 200 and await count(Outcome) == 1


async def test_cannot_log_outcome_on_another_officers_loan(officer):
    response = await post(officer, payload(loan_id="LN-2"))
    assert response.status_code == 404 and await count(Outcome) == 0


async def test_managers_cannot_log_outcomes(client):
    await client.post("/auth/login", json={"email": "manager@t.in", "password": PASSWORD})
    assert (await post(client, payload())).status_code == 403


@pytest.mark.parametrize("body,code", [
    (payload("paid", amount=None), "amount_required"),
    (payload("promise", amount=None), "amount_required"),
    (payload("not_reachable", amount=500), "amount_not_allowed"),
    (payload("dispute", amount=500), "amount_not_allowed"),
    (payload("promise", promise_date=None), "promise_date_required"),
    (payload("promise", promise_date="2026-11-08"), "promise_date_past"),
    (payload("promise", promise_date="2026-12-10"), "promise_date_too_far"),
    (payload("paid", promise_date="2026-11-12"), "promise_date_not_allowed"),
    (payload("paid", lat=22.7), "location_incomplete"),
    (payload("paid", logged_at_device=ist(10, 30).isoformat()), "logged_in_future"),
])
async def test_rule_violations_are_rejected_with_a_code(officer, body, code):
    response = await post(officer, body)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == code and response.json()["detail"]["message"]
    assert await count(Outcome) == 0


@pytest.mark.parametrize("override", [
    {"kind": "refund"}, {"amount": 0}, {"amount": -5}, {"amount": 10.555}, {"lat": 91, "lng": 75},
    {"lat": 22, "lng": -181}, {"logged_at_device": "2026-11-09T10:00:00"}, {"id": "not-a-uuid"},
])
async def test_malformed_payloads_are_rejected(officer, override):
    assert (await post(officer, payload(**override))).status_code == 422
    assert await count(Outcome) == 0


async def test_promise_dated_today_and_in_30_days_are_accepted(officer):
    assert (await post(officer, payload("promise", promise_date="2026-11-09"))).status_code == 200
    assert (await post(officer, payload("promise", promise_date="2026-12-09"))).status_code == 200


async def test_offline_promise_is_judged_by_the_day_it_was_logged(officer, set_now):
    set_now(ist(10, day=14))
    body = payload("promise", promise_date="2026-11-12", logged_at_device=ist(10).isoformat())
    assert (await post(officer, body)).status_code == 200
