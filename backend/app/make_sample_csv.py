"""Writes the sample overdue files from the seeded database. Run: uv run python -m app.make_sample_csv"""
import asyncio
import csv
import random
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import Borrower, Branch, Loan

OUT = Path(__file__).resolve().parents[2] / "sample-data"
HEADER = ["loan_id", "business_name", "business_type", "phone", "pincode",
          "outstanding", "emi", "dpd", "last_payment_date", "address"]
BRIEF_IDS = {"LN-10293", "LN-10871", "LN-11930"}


async def main() -> None:
    rng = random.Random(7)
    async with SessionLocal() as s:
        rows = (await s.execute(select(Loan, Borrower).join(Borrower, Borrower.id == Loan.borrower_id)
                                .order_by(Loan.id))).all()
        pincodes = [p for b in (await s.scalars(select(Branch).order_by(Branch.id))).all() for p in b.pincodes]
    await engine.dispose()

    table = [[l.id, b.business_name, b.business_type, b.phone, b.pincode, int(l.outstanding), int(l.emi),
              l.dpd, l.last_payment_date.isoformat() if l.last_payment_date else "", b.address]
             for l, b in rows]
    changeable = [r for r in table if r[0] not in BRIEF_IDS]
    for gone in rng.sample(changeable, 8):          # absent from today's file -> cured
        table.remove(gone)
    for row in rng.sample([r for r in table if r[0] not in BRIEF_IDS], 40):
        row[7] += rng.randint(1, 3)                  # a few more days overdue
    for n in range(12):                              # new overdue loans
        outstanding = rng.choice(range(50000, 400001, 10000))
        table.append([f"LN-{13000 + n}", f"Sample New Trader {n + 1:02d}", "grocery_store",
                      "9" + "".join(str(rng.randint(0, 9)) for _ in range(9)), rng.choice(pincodes),
                      outstanding, round(outstanding / 12, -2), rng.randint(1, 20), "2026-10-15", ""])

    OUT.mkdir(exist_ok=True)
    write(OUT / "overdue-sample.csv", table)
    bad = [
        ["LN-13100", "Sample Bad Phone", "dairy_shop", "12345", pincodes[0], 90000, 7500, 8, "2026-10-10", ""],
        ["LN-13101", "Sample Bad Pincode", "dairy_shop", "9876500001", "999999", 90000, 7500, 8, "2026-10-10", ""],
        ["LN-13102", "Sample Zero Days", "dairy_shop", "9876500002", pincodes[1], 90000, 7500, 0, "2026-10-10", ""],
        ["LN-13103", "Sample Bad Date", "dairy_shop", "9876500003", pincodes[2], 90000, 7500, 8, "10/10/2026", ""],
        [table[0][0], "Sample Repeated Loan", "dairy_shop", "9876500004", pincodes[0], 90000, 7500, 8, "", ""],
    ]
    write(OUT / "overdue-with-errors.csv", table + bad)
    print(f"{len(table)} clean rows, {len(bad)} bad rows added in the errors file")


def write(path: Path, rows: list) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows)


asyncio.run(main())
