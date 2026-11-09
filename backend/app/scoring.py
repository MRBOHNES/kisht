"""Priority score for an officer's overdue loans. Pure: no database, no clock; `today` is passed in."""
import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.models import LoanStatus, PromiseStatus

SCORING = {
    # DPD bucket -> share of points. ASSUMPTION: DPD above 30 (already rolled) gets the full share.
    "roll_risk": {"points": 35, "buckets": [(1, 10, 0.2), (11, 20, 0.5), (21, 30, 1.0)], "above": 1.0},
    "broken_promises": {"points": 25, "window_days": 90, "shares": [0, 1 / 3, 2 / 3, 1]},
    # days since last payment: under 15 -> 0, 15 to 30 -> half, over 30 or never -> full
    "last_payment": {"points": 20, "half_from": 15, "full_after": 30},
    "not_reachable": {"points": 10, "window_days": 7, "shares": [0, 1 / 3, 2 / 3, 1]},
    "promise_due_today": {"points": 10},
    # ASSUMPTION: the log scale runs from Rs 50,000 (0.8) to Rs 10,00,000 (1.2), clamped outside
    "amount_factor": {"min": 0.8, "max": 1.2, "low": 50_000, "high": 1_000_000},
    "self_cure": {"paid_within_days": 7, "multiplier": 0.5},
    "top_reasons": 3,
    "roll_limit_days": 30,
}


@dataclass(frozen=True)
class PromiseFact:
    promised_date: date
    status: PromiseStatus


@dataclass(frozen=True)
class LoanFacts:
    loan_id: str
    outstanding: Decimal | float
    dpd: int
    last_payment_date: date | None
    status: LoanStatus = LoanStatus.active
    promises: tuple[PromiseFact, ...] = ()
    not_reachable_dates: tuple[date, ...] = ()


@dataclass(frozen=True)
class Reason:
    key: str
    points: int
    text_en: str
    text_hi: str


@dataclass(frozen=True)
class LoanScore:
    loan_id: str
    risk: int
    amount_factor: float
    priority: float
    self_cure: str | None  # "paid_recently" | "promise_pending" | None
    low_confidence: bool
    reasons: list[Reason] = field(default_factory=list)  # top 3, highest points first


def score_loan(facts: LoanFacts, today: date) -> LoanScore:
    reasons = [r for r in all_reasons(facts, today) if r.points > 0]
    risk = sum(r.points for r in reasons)
    factor = amount_factor(facts.outstanding)
    cure = self_cure(facts, today)
    priority = risk * factor * (SCORING["self_cure"]["multiplier"] if cure else 1)
    top = sorted(reasons, key=lambda r: -r.points)[: SCORING["top_reasons"]]
    return LoanScore(
        loan_id=facts.loan_id, risk=risk, amount_factor=round(factor, 3), priority=round(priority, 1),
        self_cure=cure, low_confidence=facts.last_payment_date is None and not facts.promises, reasons=top,
    )


def priority_list(loans: list[LoanFacts], today: date) -> list[LoanScore]:
    """Active loans only (disputed and cured are left out), highest value at risk first."""
    dpd_of = {f.loan_id: f.dpd for f in loans}
    scores = [score_loan(f, today) for f in loans if f.status == LoanStatus.active]
    return sorted(scores, key=lambda s: (-s.priority, -dpd_of[s.loan_id], s.loan_id))


def all_reasons(f: LoanFacts, today: date) -> list[Reason]:
    return [
        roll_risk(f.dpd),
        broken_promises(f.promises, today),
        last_payment(f.last_payment_date, today),
        not_reachable(f.not_reachable_dates, today),
        promise_due_today(f.promises, today),
    ]


def points(factor: str, share: float) -> int:
    return math.floor(SCORING[factor]["points"] * share + 0.5)


def count_share(factor: str, count: int) -> float:
    shares = SCORING[factor]["shares"]
    return shares[min(count, len(shares) - 1)]


def roll_risk(dpd: int) -> Reason:
    cfg = SCORING["roll_risk"]
    share = next((s for lo, hi, s in cfg["buckets"] if lo <= dpd <= hi), cfg["above"] if dpd > 0 else 0)
    left = SCORING["roll_limit_days"] - dpd
    if left > 0:
        en, hi = f"{dpd} days overdue: crosses 30 in {left} days", f"{dpd} दिन बकाया: {left} दिन में 30 पार"
    elif left == 0:
        en, hi = f"{dpd} days overdue: at the 30-day limit", f"{dpd} दिन बकाया: 30 दिन की सीमा पर"
    else:
        en, hi = f"{dpd} days overdue: past 30", f"{dpd} दिन बकाया: 30 पार"
    return Reason("roll_risk", points("roll_risk", share), en, hi)


def is_broken(p: PromiseFact, today: date) -> bool:
    # an open promise whose date has passed counts as broken
    return p.status == PromiseStatus.broken or (p.status == PromiseStatus.open and p.promised_date < today)


def broken_promises(promises: tuple[PromiseFact, ...], today: date) -> Reason:
    window = SCORING["broken_promises"]["window_days"]
    n = sum(1 for p in promises if is_broken(p, today) and 0 <= (today - p.promised_date).days <= window)
    en = f"{n} promise broken in 90 days" if n == 1 else f"{n} promises broken in 90 days"
    hi = f"90 दिन में {n} वादा टूटा" if n == 1 else f"90 दिन में {n} वादे टूटे"
    return Reason("broken_promises", points("broken_promises", count_share("broken_promises", n)), en, hi)


def last_payment(last_paid: date | None, today: date) -> Reason:
    cfg = SCORING["last_payment"]
    if last_paid is None:
        return Reason("last_payment", points("last_payment", 1), "Never paid", "कभी भुगतान नहीं")
    days = (today - last_paid).days
    share = 0 if days < cfg["half_from"] else 0.5 if days <= cfg["full_after"] else 1
    return Reason("last_payment", points("last_payment", share),
                  f"No payment for {days} days", f"{days} दिन से कोई भुगतान नहीं")


def not_reachable(dates: tuple[date, ...], today: date) -> Reason:
    window = SCORING["not_reachable"]["window_days"]
    n = sum(1 for d in dates if 0 <= (today - d).days < window)
    en = f"Not reachable {n} {'time' if n == 1 else 'times'} in 7 days"
    hi = f"7 दिन में {n} बार संपर्क नहीं"
    return Reason("not_reachable", points("not_reachable", count_share("not_reachable", n)), en, hi)


def promise_due_today(promises: tuple[PromiseFact, ...], today: date) -> Reason:
    due = any(p.status == PromiseStatus.open and p.promised_date == today for p in promises)
    return Reason("promise_due_today", points("promise_due_today", 1 if due else 0),
                  "Promise due today", "आज वादे की तारीख")


def amount_factor(outstanding: Decimal | float) -> float:
    cfg = SCORING["amount_factor"]
    amount = min(max(float(outstanding), cfg["low"]), cfg["high"])
    position = math.log(amount / cfg["low"]) / math.log(cfg["high"] / cfg["low"])
    return cfg["min"] + (cfg["max"] - cfg["min"]) * position


def self_cure(f: LoanFacts, today: date) -> str | None:
    if f.last_payment_date and (today - f.last_payment_date).days < SCORING["self_cure"]["paid_within_days"]:
        return "paid_recently"
    if any(p.status == PromiseStatus.open and p.promised_date > today for p in f.promises):
        return "promise_pending"
    return None
