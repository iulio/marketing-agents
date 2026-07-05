# app/seasonal.py
from datetime import datetime
from typing import List


def get_upcoming_events() -> List[str]:
    now = datetime.now()
    month = now.month
    day = now.day
    events = []

    if month == 1 and day <= 7:
        events.append("New Year")
    if month == 2 and day <= 14:
        events.append("Valentine's Day")
    if month == 3:
        events.append("International Women's Day")
    if month == 4:
        events.append("Easter")
    if month == 5 and day <= 14:
        events.append("Mother's Day")
    if month == 5:
        events.append("Labour Day")
    if month == 6 and day <= 21:
        events.append("Father's Day")
    if month == 10 and day <= 31:
        events.append("Halloween")
    if month == 11 and day <= 11:
        events.append("Black Friday")
    if month == 12 and day <= 1:
        events.append("1 Decembrie (Romanian National Day)")
    if month == 12 and day <= 25:
        events.append("Christmas")
    if month == 12 and day >= 26:
        events.append("New Year's Eve")

    return events