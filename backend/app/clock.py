from datetime import date, datetime, timedelta, timezone

# India has no daylight saving, so a fixed offset is exact and needs no tz database
IST = timezone(timedelta(hours=5, minutes=30))


def today_ist() -> date:
    return datetime.now(IST).date()


def ist_day_start(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time(), IST)


def current_time() -> datetime:
    """FastAPI dependency, so tests can pin the clock."""
    return datetime.now(timezone.utc)


def ist_date(at: datetime) -> date:
    return at.astimezone(IST).date()
