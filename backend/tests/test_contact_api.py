from datetime import datetime

import pytest
from sqlalchemy import select

from app.clock import IST
from app.db import SessionLocal
from app.models import ContactAttempt
from tests.world import PASSWORD, add_loan, reset_world


@pytest.fixture(autouse=True)
async def world():
    return await reset_world()


async def login(client, email="asha@t.in"):
    await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    return client


def ist(hour, minute=0):
    return datetime(2026, 11, 9, hour, minute, tzinfo=IST)


async def attempts():
    async with SessionLocal() as s:
        return (await s.scalars(select(ContactAttempt).order_by(ContactAttempt.id))).all()


async def call(client, loan_id="LN-1", kind="call"):
    return await client.post(f"/loans/{loan_id}/contact", json={"type": kind})


@pytest.mark.parametrize("hour,minute,status", [(7, 59, 403), (8, 0, 200), (18, 59, 200), (19, 0, 403)])
async def test_call_is_checked_against_contact_window(client, world, set_now, hour, minute, status):
    await add_loan("LN-1", world["asha"])
    set_now(ist(hour, minute))
    response = await call(await login(client))
    assert response.status_code == status
    stored = await attempts()
    assert len(stored) == 1 and stored[0].allowed is (status == 200)


async def test_blocked_call_is_stored_with_reason_and_hides_phone(client, world, set_now):
    await add_loan("LN-1", world["asha"], phone="9876543210")
    set_now(ist(7, 30))
    response = await call(await login(client))
    detail = response.json()["detail"]
    assert detail["code"] == "outside_contact_hours" and "08:00-19:00" in detail["message"]
    assert detail["attempt"]["allowed"] is False
    assert "9876543210" not in response.text
    assert (await attempts())[0].blocked_reason == detail["message"]


async def test_allowed_call_returns_phone_for_tel_link(client, world, set_now):
    await add_loan("LN-1", world["asha"], phone="9876543210")
    set_now(ist(10))
    body = (await call(await login(client))).json()
    assert body["phone"] == "9876543210" and body["attempt"]["type"] == "call"


async def test_visit_attempt_does_not_return_phone(client, world, set_now):
    await add_loan("LN-1", world["asha"])
    set_now(ist(10))
    assert (await call(await login(client), kind="visit")).json()["phone"] is None


async def test_cannot_contact_another_officers_borrower(client, world, set_now):
    await add_loan("LN-1", world["bala"])
    set_now(ist(10))
    assert (await call(await login(client))).status_code == 404
    assert await attempts() == []


async def test_managers_do_not_log_contact_attempts(client, world, set_now):
    await add_loan("LN-1", world["asha"])
    set_now(ist(10))
    assert (await call(await login(client, "manager@t.in"))).status_code == 403


async def test_unknown_contact_type_is_rejected(client, world, set_now):
    await add_loan("LN-1", world["asha"])
    set_now(ist(10))
    assert (await call(await login(client), kind="sms")).status_code == 422
    assert await attempts() == []
