# app/seasonal.py
from datetime import datetime

def get_upcoming_events() -> List[str]:
    now = datetime.now()
    month = now.month
    day = now.day
    events = []
    if month == 2 and day <= 14:
        events.append("Valentine's Day")
    if month == 5 and day <= 14:
        events.append("Mother's Day")
    if month == 6 and day <= 21:
        events.append("Father's Day")
    if month == 12 and day <= 25:
        events.append("Christmas")
    return events