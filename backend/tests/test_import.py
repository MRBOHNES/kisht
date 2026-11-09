import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Loan, LoanStatus
from tests.world import PASSWORD, PINCODE_A, PINCODE_B, csv_text, good_row, reset_world


@pytest.fixture(autouse=True)
async def world():
    return await reset_world()


@pytest.fixture
async def manager(client):
    await client.post("/auth/login", json={"email": "manager@t.in", "password": PASSWORD})
    return client


async def upload(client, *rows, raw=None):
    data = raw if raw is not None else csv_text(*rows).encode()
    return await client.post("/imports", files={"file": ("overdue.csv", data, "text/csv")})


async def loans_by_id():
    async with SessionLocal() as s:
        return {l.id: l for l in (await s.scalars(select(Loan))).all()}


async def test_new_loans_go_to_branch_by_pincode(manager, world):
    body = (await upload(manager, good_row("LN-1", PINCODE_A), good_row("LN-2", PINCODE_B))).json()
    loans = await loans_by_id()
    assert loans["LN-2"].officer_id == world["chitra"]
    assert loans["LN-1"].officer_id in (world["asha"], world["bala"])
    assert body["assigned"] == 2


async def test_workload_balances_within_branch(manager, world):
    await upload(manager, *[good_row(f"LN-{i}", PINCODE_A) for i in range(1, 7)])
    loans = await loans_by_id()
    counts = {}
    for loan in loans.values():
        counts[loan.officer_id] = counts.get(loan.officer_id, 0) + 1
    assert counts == {world["asha"]: 3, world["bala"]: 3}


async def test_new_loan_goes_to_officer_with_fewer_open_loans(manager, world):
    await upload(manager, good_row("LN-1"), good_row("LN-2"))
    async with SessionLocal() as s:
        loan = await s.get(Loan, "LN-1")
        loan.status = LoanStatus.cured
        await s.commit()
    await upload(manager, good_row("LN-2"), good_row("LN-3"))
    loans = await loans_by_id()
    assert loans["LN-3"].officer_id != loans["LN-2"].officer_id


async def test_summary_counts_and_errors(manager):
    body = (await upload(manager, good_row("LN-1"), good_row("LN-2", phone="bad"))).json()
    assert (body["rows"], body["imported"], body["not_imported"], body["assigned"]) == (2, 1, 1, 1)
    assert body["errors"][0]["row"] == 3 and body["errors"][0]["fix"]
    assert sum(r["open_loans"] for r in body["assignment"]) == 1
    assert sum(r["new_in_import"] for r in body["assignment"]) == 1


async def test_reimport_updates_figures_and_keeps_officer(manager):
    await upload(manager, good_row("LN-1", dpd="12"))
    before = (await loans_by_id())["LN-1"].officer_id
    body = (await upload(manager, good_row("LN-1", dpd="15", outstanding="50000"))).json()
    after = (await loans_by_id())["LN-1"]
    assert (body["created"], body["updated"], body["cured"]) == (0, 1, 0)
    assert after.dpd == 15 and int(after.outstanding) == 50000 and after.officer_id == before


async def test_loans_missing_from_file_are_cured_not_deleted(manager):
    await upload(manager, good_row("LN-1"), good_row("LN-2"))
    body = (await upload(manager, good_row("LN-1"))).json()
    loans = await loans_by_id()
    assert body["cured"] == 1
    assert loans["LN-2"].status == LoanStatus.cured and loans["LN-1"].status == LoanStatus.active
    assert sum(r["open_loans"] for r in body["assignment"]) == 1


async def test_cured_loan_is_not_cured_twice(manager):
    await upload(manager, good_row("LN-1"), good_row("LN-2"))
    await upload(manager, good_row("LN-1"))
    assert (await upload(manager, good_row("LN-1"))).json()["cured"] == 0


async def test_row_with_error_does_not_cure_its_loan(manager):
    await upload(manager, good_row("LN-1"), good_row("LN-2"))
    body = (await upload(manager, good_row("LN-1"), good_row("LN-2", phone="bad"))).json()
    assert body["cured"] == 0
    assert (await loans_by_id())["LN-2"].status == LoanStatus.active


async def test_cured_loan_reappearing_becomes_active_again(manager):
    await upload(manager, good_row("LN-1"), good_row("LN-2"))
    await upload(manager, good_row("LN-1"))
    await upload(manager, good_row("LN-1"), good_row("LN-2"))
    assert (await loans_by_id())["LN-2"].status == LoanStatus.active


async def test_disputed_loan_keeps_status_on_update(manager):
    await upload(manager, good_row("LN-1"))
    async with SessionLocal() as s:
        (await s.get(Loan, "LN-1")).status = LoanStatus.paused_dispute
        await s.commit()
    await upload(manager, good_row("LN-1", dpd="20"))
    assert (await loans_by_id())["LN-1"].status == LoanStatus.paused_dispute


async def test_empty_file_is_rejected_and_cures_nothing(manager):
    await upload(manager, good_row("LN-1"))
    response = await upload(manager)
    assert response.status_code == 400
    assert (await loans_by_id())["LN-1"].status == LoanStatus.active


async def test_missing_column_is_rejected_with_names(manager):
    response = await upload(manager, raw=b"loan_id,dpd\nLN-1,3\n")
    assert response.status_code == 400
    assert "pincode" in response.json()["detail"]["columns"]


async def test_non_utf8_file_is_rejected(manager):
    assert (await upload(manager, raw=b"\xff\xfe\x00bad")).status_code == 400


async def test_officer_cannot_import_csv(client):
    await client.post("/auth/login", json={"email": "asha@t.in", "password": PASSWORD})
    assert (await upload(client, good_row())).status_code == 403
    assert await loans_by_id() == {}


async def test_import_requires_login(client):
    assert (await upload(client, good_row())).status_code == 401


async def test_file_with_no_valid_rows_cures_nothing(manager):
    await upload(manager, good_row("LN-1"), good_row("LN-2"))
    body = (await upload(manager, good_row("LN 1"), good_row("", phone="bad"))).json()
    assert body["cured"] == 0 and body["not_imported"] == 2
    assert {l.status for l in (await loans_by_id()).values()} == {LoanStatus.active}

