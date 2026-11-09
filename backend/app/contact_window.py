from datetime import datetime, time

from app.clock import IST

# ASSUMPTION: 08:00 to 19:00 India time, start inclusive, end exclusive
START, END = time(8, 0), time(19, 0)
BLOCKED_REASON = "Outside contact hours 08:00-19:00 IST (RBI rules)"


def in_contact_window(at: datetime) -> bool:
    local = at.astimezone(IST).time()
    return START <= local < END
