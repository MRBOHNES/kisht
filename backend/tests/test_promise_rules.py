from datetime import date, datetime

import pytest
from sqlalchemy import select

from app.clock import IST
from app.db import SessionLocal
from app.models import Promise, PromiseStatus
from app.promises import mark_broken, mark_kept
from tests.world import add, add_loan, reset_world

TODAY = date(2026, 11, 9)


@pytest.fixture(autouse=True)
async def world():
    ids = await reset_world()
    await add_loan("LN-1", ids["asha"])
    await add_loan("LN-2", ids["asha"])
    return ids


def promise(day: int, status=PromiseStatus.open, loan_id="LN-1", made_day: int = 1):
    return Promise(loan_id=loan_id, officer_id=1, amount=5000, promised_date=date(2026, 11, day), status=status,
                   created_at=datetime(2026, 11, made_day, 10, tzinfo=IST))


async def statuses():
    async with SessionLocal() as s:
        rows = (await s.scalars(select(Promise).order_by(Promise.id))).all()
    return [p.status for p in rows]


async def run(rule, *args):
    async with SessionLocal() as s:
        await rule(s, *args)
        await s.commit()


async def test_open_promise_past_its_date_becomes_broken():
    await add(promise(8), promise(9), promise(10))
    await run(mark_broken, TODAY)
    assert await statuses() == [PromiseStatus.broken, PromiseStatus.open, PromiseStatus.open]


async def test_mark_broken_leaves_kept_promises_alone():
    await add(promise(5, PromiseStatus.kept))
    await run(mark_broken, TODAY)
    assert await statuses() == [PromiseStatus.kept]


async def test_mark_broken_can_be_limited_to_some_loans():
    await add(promise(5), promise(5, loan_id="LN-2"))
    await run(mark_broken, TODAY, ["LN-2"])
    assert await statuses() == [PromiseStatus.open, PromiseStatus.broken]


async def test_payment_keeps_open_promise_due_on_or_after_payment_day():
    await add(promise(9), promise(12))
    await run(mark_kept, "LN-1", datetime(2026, 11, 9, 11, tzinfo=IST))
    assert await statuses() == [PromiseStatus.kept, PromiseStatus.kept]


async def test_payment_after_the_date_does_not_keep_the_promise():
    await add(promise(8, PromiseStatus.broken))
    await run(mark_kept, "LN-1", datetime(2026, 11, 9, 11, tzinfo=IST))
    assert await statuses() == [PromiseStatus.broken]


async def test_late_synced_payment_revives_promise_it_met_in_time():
    await add(promise(10))
    await run(mark_broken, date(2026, 11, 12))
    await run(mark_kept, "LN-1", datetime(2026, 11, 10, 9, tzinfo=IST))
    assert await statuses() == [PromiseStatus.kept]


async def test_payment_does_not_keep_a_promise_made_after_it():
    await add(promise(12, made_day=10))
    await run(mark_kept, "LN-1", datetime(2026, 11, 9, 11, tzinfo=IST))
    assert await statuses() == [PromiseStatus.open]


async def test_payment_only_touches_its_own_loan():
    await add(promise(12, loan_id="LN-2"))
    await run(mark_kept, "LN-1", datetime(2026, 11, 9, 11, tzinfo=IST))
    assert await statuses() == [PromiseStatus.open]
