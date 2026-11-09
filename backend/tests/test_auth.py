from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from tests.world import PASSWORD, reset_world


@pytest.fixture(autouse=True)
async def world():
    return await reset_world()


async def login(client, email="asha@t.in", password=PASSWORD):
    return await client.post("/auth/login", json={"email": email, "password": password})


async def test_login_sets_httponly_cookie_and_returns_role(client):
    response = await login(client)
    assert response.status_code == 200
    assert response.json()["role"] == "field_officer"
    assert "httponly" in response.headers["set-cookie"].lower()
    assert (await client.get("/auth/me")).json()["email"] == "asha@t.in"


async def test_role_comes_from_account(client):
    await login(client, "manager@t.in")
    assert (await client.get("/auth/me")).json()["role"] == "branch_manager"


async def test_wrong_password_and_unknown_email_look_the_same(client):
    wrong = await login(client, password="nope")
    unknown = await login(client, email="ghost@t.in", password="nope")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_me_requires_login(client):
    assert (await client.get("/auth/me")).status_code == 401


async def test_account_locks_after_five_failures_even_for_right_password(client):
    for _ in range(4):
        assert (await login(client, password="nope")).status_code == 401
    assert (await login(client, password="nope")).status_code == 423
    locked = await login(client)
    assert locked.status_code == 423
    assert locked.json()["detail"]["code"] == "locked"


async def test_lock_expires_and_counter_resets(client):
    for _ in range(5):
        await login(client, password="nope")
    async with SessionLocal() as s:
        user = await s.scalar(select(User).where(User.email == "asha@t.in"))
        user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        await s.commit()
    assert (await login(client)).status_code == 200
    async with SessionLocal() as s:
        user = await s.scalar(select(User).where(User.email == "asha@t.in"))
        assert user.failed_logins == 0 and user.locked_until is None


async def test_success_resets_failed_counter(client):
    for _ in range(3):
        await login(client, password="nope")
    await login(client)
    for _ in range(4):
        assert (await login(client, password="nope")).status_code == 401


async def test_lock_lasts_fifteen_minutes(client):
    for _ in range(5):
        await login(client, password="nope")
    async with SessionLocal() as s:
        user = await s.scalar(select(User).where(User.email == "asha@t.in"))
        remaining = user.locked_until - datetime.now(timezone.utc)
    assert timedelta(minutes=14) < remaining <= timedelta(minutes=15)



async def test_password_longer_than_bcrypt_limit_is_a_normal_failure(client):
    assert (await login(client, password="x" * 80)).status_code == 401
    assert (await login(client, email="ghost@t.in", password="पासवर्ड" * 10)).status_code == 401
