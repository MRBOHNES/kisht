from datetime import date

from app.rollrate import roll_rates

JUL, AUG, SEP = date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1)


def test_share_of_bucket_loans_that_pass_30_next_month():
    rows = [("A", JUL, 10), ("B", JUL, 29), ("C", JUL, 5), ("D", JUL, 30),
            ("A", AUG, 12), ("B", AUG, 31), ("C", AUG, 0), ("D", AUG, 45)]
    [step] = roll_rates(rows)
    assert (step["month"], step["base"], step["rolled"], step["rate"]) == ("2026-08-01", 4, 2, 0.5)


def test_bucket_edges_dpd_1_and_30_count_and_31_does_not():
    rows = [("A", JUL, 1), ("B", JUL, 30), ("C", JUL, 31), ("D", JUL, 0),
            ("A", AUG, 40), ("B", AUG, 40), ("C", AUG, 60), ("D", AUG, 40)]
    assert roll_rates(rows)[0]["base"] == 2


def test_loan_that_left_the_book_counts_as_not_rolled():
    rows = [("A", JUL, 20), ("B", JUL, 20), ("A", AUG, 35)]
    step = roll_rates(rows)[0]
    assert (step["base"], step["rolled"], step["rate"]) == (2, 1, 0.5)


def test_one_step_per_pair_of_months_oldest_first():
    rows = [("A", SEP, 10), ("A", JUL, 10), ("A", AUG, 40)]
    assert [s["month"] for s in roll_rates(rows)] == ["2026-08-01", "2026-09-01"]
    assert [s["rate"] for s in roll_rates(rows)] == [1.0, None]


def test_no_snapshots_means_no_steps():
    assert roll_rates([]) == []
