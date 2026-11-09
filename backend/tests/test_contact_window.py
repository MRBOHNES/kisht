from datetime import datetime, timezone

import pytest

from app.clock import IST
from app.contact_window import in_contact_window


@pytest.mark.parametrize("hour,minute,allowed", [
    (7, 59, False), (8, 0, True), (12, 0, True), (18, 59, True), (19, 0, False), (23, 30, False), (0, 0, False),
])
def test_contact_window_boundaries_in_ist(hour, minute, allowed):
    assert in_contact_window(datetime(2026, 11, 9, hour, minute, tzinfo=IST)) is allowed


def test_last_second_before_seven_is_allowed():
    assert in_contact_window(datetime(2026, 11, 9, 18, 59, 59, tzinfo=IST))


def test_utc_times_are_converted_to_ist():
    # 02:30 UTC is 08:00 IST; 13:30 UTC is 19:00 IST
    assert in_contact_window(datetime(2026, 11, 9, 2, 30, tzinfo=timezone.utc))
    assert not in_contact_window(datetime(2026, 11, 9, 13, 30, tzinfo=timezone.utc))
    assert not in_contact_window(datetime(2026, 11, 9, 2, 29, tzinfo=timezone.utc))
