from app.assignment import pick_officer
from app.models import User


def test_prefers_officer_with_fewest_open_loans():
    a, b = User(id=1), User(id=2)
    assert pick_officer([a, b], {1: 3, 2: 1}) is b


def test_tie_goes_to_lowest_id():
    a, b = User(id=1), User(id=2)
    assert pick_officer([b, a], {1: 2, 2: 2}) is a


def test_officer_with_no_loans_counts_as_zero():
    a, b = User(id=1), User(id=2)
    assert pick_officer([a, b], {1: 1}) is b
