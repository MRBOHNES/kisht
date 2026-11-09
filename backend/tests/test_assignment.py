from sqlalchemy import update

from app.assignment import pick_officer
from app.db import SessionLocal
from app.models import Role, User
from tests.world import PASSWORD, PINCODE_A, PINCODE_B, csv_text, good_row, reset_world


def test_prefers_officer_with_fewest_open_loans():
    a, b = User(id=1), User(id=2)
    assert pick_officer([a, b], {1: 3, 2: 1}) is b


def test_tie_goes_to_lowest_id():
    a, b = User(id=1), User(id=2)
    assert pick_officer([b, a], {1: 2, 2: 2}) is a


def test_officer_with_no_loans_counts_as_zero():
    a, b = User(id=1), User(id=2)
    assert pick_officer([a, b], {1: 1}) is b

async def test_pincode_of_branch_without_officers_is_a_row_error(client):
    await reset_world()
    await client.post("/auth/login", json={"email": "manager@t.in", "password": PASSWORD})
    async with SessionLocal() as s:
        await s.execute(update(User).where(User.role == Role.field_officer, User.branch_id == 2)
                        .values(role=Role.branch_manager))
        await s.commit()
    csv = csv_text(good_row("LN-1", PINCODE_B), good_row("LN-2", PINCODE_A)).encode()
    body = (await client.post("/imports", files={"file": ("o.csv", csv, "text/csv")})).json()
    assert body["imported"] == 1
    assert body["errors"][0]["field"] == "pincode" and body["errors"][0]["row"] == 2
