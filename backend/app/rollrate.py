"""Roll rate: of the loans 1-30 days past due at one month end, the share past 30 at the next."""
from collections import defaultdict
from datetime import date

ROLL_TARGET = 0.16
BUCKET = (1, 30)


def roll_rates(snapshots: list[tuple[str, date, int]]) -> list[dict]:
    """Takes (loan_id, month, dpd) rows; returns one entry per month-to-month step, oldest first.

    A loan missing from the next month's snapshot has left the overdue book, so it counts
    in the base as not rolled.
    """
    by_month: dict[date, dict[str, int]] = defaultdict(dict)
    for loan_id, month, dpd in snapshots:
        by_month[month][loan_id] = dpd
    months = sorted(by_month)
    steps = []
    for prev, nxt in zip(months, months[1:]):
        base = [loan for loan, dpd in by_month[prev].items() if BUCKET[0] <= dpd <= BUCKET[1]]
        rolled = sum(1 for loan in base if by_month[nxt].get(loan, 0) > BUCKET[1])
        steps.append({
            "from_month": prev.isoformat(), "month": nxt.isoformat(), "base": len(base), "rolled": rolled,
            "rate": round(rolled / len(base), 3) if base else None,
        })
    return steps
