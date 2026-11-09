import math
from datetime import date, timedelta

import pytest

from app.models import LoanStatus, PromiseStatus
from app.scoring import LoanFacts, PromiseFact, all_reasons, amount_factor, priority_list, score_loan

TODAY = date(2026, 11, 9)


def days_ago(n: int) -> date:
    return TODAY - timedelta(days=n)


def facts(**over) -> LoanFacts:
    base = dict(loan_id="LN-1", outstanding=223_607, dpd=5, last_payment_date=days_ago(3))
    base.update(over)
    return LoanFacts(**base)


def factor_points(f: LoanFacts) -> dict[str, int]:
    # score_loan keeps only the top 3 non-zero reasons, so read every factor directly
    return {r.key: r.points for r in all_reasons(f, TODAY)}


def promise(day_offset: int, status=PromiseStatus.broken) -> PromiseFact:
    return PromiseFact(TODAY + timedelta(days=day_offset), status)


@pytest.mark.parametrize("dpd,expected", [(1, 7), (10, 7), (11, 18), (20, 18), (21, 35), (30, 35), (31, 35)])
def test_roll_risk_buckets(dpd, expected):
    assert factor_points(facts(dpd=dpd))["roll_risk"] == expected


@pytest.mark.parametrize("count,expected", [(0, 0), (1, 8), (2, 17), (3, 25), (5, 25)])
def test_broken_promises_steps(count, expected):
    f = facts(promises=tuple(promise(-10 - i) for i in range(count)))
    assert factor_points(f)["broken_promises"] == expected


def test_broken_promise_window_is_90_days():
    assert factor_points(facts(promises=(promise(-90),)))["broken_promises"] == 8
    assert factor_points(facts(promises=(promise(-91),)))["broken_promises"] == 0


def test_open_promise_past_its_date_counts_as_broken():
    f = facts(promises=(promise(-1, PromiseStatus.open),))
    assert factor_points(f)["broken_promises"] == 8


def test_kept_and_not_yet_due_promises_are_not_broken():
    f = facts(promises=(promise(-5, PromiseStatus.kept), promise(0, PromiseStatus.open), promise(2, PromiseStatus.open)))
    assert factor_points(f)["broken_promises"] == 0


@pytest.mark.parametrize("days,expected", [(14, 0), (15, 10), (30, 10), (31, 20)])
def test_last_payment_steps(days, expected):
    assert factor_points(facts(last_payment_date=days_ago(days)))["last_payment"] == expected


def test_never_paid_gets_full_last_payment_points():
    assert factor_points(facts(last_payment_date=None))["last_payment"] == 20


@pytest.mark.parametrize("count,expected", [(0, 0), (1, 3), (2, 7), (3, 10), (4, 10)])
def test_not_reachable_steps(count, expected):
    f = facts(not_reachable_dates=tuple(days_ago(i) for i in range(count)))
    assert factor_points(f)["not_reachable"] == expected


def test_not_reachable_window_is_last_7_days():
    assert factor_points(facts(not_reachable_dates=(days_ago(6),)))["not_reachable"] == 3
    assert factor_points(facts(not_reachable_dates=(days_ago(7),)))["not_reachable"] == 0


def test_promise_due_today_only_counts_today():
    assert factor_points(facts(promises=(promise(0, PromiseStatus.open),)))["promise_due_today"] == 10
    assert factor_points(facts(promises=(promise(1, PromiseStatus.open),)))["promise_due_today"] == 0
    assert factor_points(facts(promises=(promise(0, PromiseStatus.kept),)))["promise_due_today"] == 0


def test_risk_is_sum_and_maxes_at_100():
    f = facts(dpd=28, last_payment_date=None,
              promises=(promise(-5), promise(-6), promise(-7), promise(0, PromiseStatus.open)),
              not_reachable_dates=(days_ago(0), days_ago(1), days_ago(2)))
    assert score_loan(f, TODAY).risk == 100


@pytest.mark.parametrize("amount,expected", [(10_000, 0.8), (50_000, 0.8), (1_000_000, 1.2), (5_000_000, 1.2)])
def test_amount_factor_is_clamped(amount, expected):
    assert amount_factor(amount) == pytest.approx(expected)


def test_amount_factor_is_log_scaled():
    midpoint = math.sqrt(50_000 * 1_000_000)  # geometric mean sits halfway on a log scale
    assert amount_factor(midpoint) == pytest.approx(1.0)
    assert amount_factor(640_000) > amount_factor(310_000) > amount_factor(220_000)


def test_priority_is_risk_times_amount_factor():
    s = score_loan(facts(dpd=25, outstanding=1_000_000, last_payment_date=days_ago(20)), TODAY)
    assert s.risk == 45
    assert s.priority == pytest.approx(54.0)


def test_self_cure_halves_priority_when_paid_in_last_7_days():
    paid = score_loan(facts(dpd=25, last_payment_date=days_ago(6)), TODAY)
    not_paid = score_loan(facts(dpd=25, last_payment_date=days_ago(7)), TODAY)
    assert paid.self_cure == "paid_recently" and not_paid.self_cure is None
    assert paid.priority == pytest.approx(paid.risk * paid.amount_factor * 0.5, abs=0.1)


def test_self_cure_for_open_promise_not_yet_due():
    s = score_loan(facts(dpd=25, last_payment_date=days_ago(20), promises=(promise(2, PromiseStatus.open),)), TODAY)
    assert s.self_cure == "promise_pending"
    assert s.priority == pytest.approx(s.risk * s.amount_factor * 0.5, abs=0.1)


def test_promise_due_today_is_not_self_cure():
    s = score_loan(facts(dpd=25, last_payment_date=days_ago(20), promises=(promise(0, PromiseStatus.open),)), TODAY)
    assert s.self_cure is None


def test_low_confidence_when_no_payment_and_no_promise_history():
    assert score_loan(facts(last_payment_date=None), TODAY).low_confidence
    assert not score_loan(facts(last_payment_date=None, promises=(promise(-5),)), TODAY).low_confidence
    assert not score_loan(facts(), TODAY).low_confidence


def test_top_three_reasons_highest_points_first_with_both_languages():
    f = facts(dpd=28, last_payment_date=days_ago(20), promises=(promise(-5), promise(-8)),
              not_reachable_dates=(days_ago(1),))
    reasons = score_loan(f, TODAY).reasons
    assert [(r.key, r.points) for r in reasons] == [("roll_risk", 35), ("broken_promises", 17), ("last_payment", 10)]
    assert reasons[0].text_hi == "28 दिन बकाया: 2 दिन में 30 पार"
    assert reasons[0].text_en == "28 days overdue: crosses 30 in 2 days"


def test_zero_point_factors_are_not_reasons():
    reasons = score_loan(facts(dpd=5, last_payment_date=days_ago(3)), TODAY).reasons
    assert [r.key for r in reasons] == ["roll_risk"]


def test_dispute_and_cured_loans_are_left_out_of_the_list():
    loans = [facts(loan_id="LN-1"), facts(loan_id="LN-2", status=LoanStatus.paused_dispute),
             facts(loan_id="LN-3", status=LoanStatus.cured)]
    assert [s.loan_id for s in priority_list(loans, TODAY)] == ["LN-1"]


def test_list_sorted_by_value_at_risk():
    small_urgent = facts(loan_id="LN-1", dpd=28, outstanding=50_000, last_payment_date=days_ago(20))
    big_urgent = facts(loan_id="LN-2", dpd=28, outstanding=1_000_000, last_payment_date=days_ago(20))
    mild = facts(loan_id="LN-3", dpd=3, outstanding=1_000_000)
    assert [s.loan_id for s in priority_list([mild, small_urgent, big_urgent], TODAY)] == ["LN-2", "LN-1", "LN-3"]


def test_scoring_does_not_depend_on_input_order():
    loans = [facts(loan_id=f"LN-{i}", dpd=i) for i in range(1, 8)]
    assert priority_list(loans, TODAY) == priority_list(list(reversed(loans)), TODAY)
