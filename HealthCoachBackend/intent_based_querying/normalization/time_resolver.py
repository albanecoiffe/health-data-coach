# "hier", "7 derniers jours", etc. -> (start,end)

# time_resolver.py
from datetime import datetime, date, timedelta
from typing import Tuple

# --------------------------------------------------
# Helpers
# --------------------------------------------------


def start_of_day(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 0, 0, 0)


def start_of_week(d: date) -> date:
    """
    ISO week: lundi = 0
    """
    return d - timedelta(days=d.weekday())


def start_of_month(d: date) -> date:
    return date(d.year, d.month, 1)


def start_of_year(d: date) -> date:
    return date(d.year, 1, 1)


# --------------------------------------------------
# Main resolver
# --------------------------------------------------

from datetime import date, timedelta


def resolve_period(period: str):
    today = date.today()
    print("\n🕒 TIME RESOLUTION")
    print("➡️ Period keyword :", period)

    if period == "today":
        print("✅ Resolved period :", today, "→", today + timedelta(days=1))
        return today, today + timedelta(days=1)

    if period == "yesterday":
        y = today - timedelta(days=1)
        print("✅ Resolved period :", y, "→", today)
        return y, today

    if period == "this_week":
        start = today - timedelta(days=today.weekday())
        print("✅ Resolved period :", start, "→", start + timedelta(days=7))
        return start, start + timedelta(days=7)

    if period == "last_week":
        end = today - timedelta(days=today.weekday())
        start = end - timedelta(days=7)
        print("✅ Resolved period :", start, "→", end)
        return start, end

    if period == "last_7_days":
        print("✅ Resolved period :", today - timedelta(days=7), "→", today)
        return today - timedelta(days=7), today

    if period == "this_month":
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        print("✅ Resolved period :", start, "→", end)
        return start, end

    if period == "last_month":
        first = today.replace(day=1)
        end = first
        if first.month == 1:
            start = first.replace(year=first.year - 1, month=12)
        else:
            start = first.replace(month=first.month - 1)
        print("✅ Resolved period :", start, "→", end)
        return start, end

    if period == "this_year":
        print(
            "✅ Resolved period :",
            date(today.year, 1, 1),
            "→",
            date(today.year + 1, 1, 1),
        )
        return date(today.year, 1, 1), date(today.year + 1, 1, 1)

    if period == "last_year":
        print(
            "✅ Resolved period :",
            date(today.year - 1, 1, 1),
            "→",
            date(today.year, 1, 1),
        )
        return date(today.year - 1, 1, 1), date(today.year, 1, 1)

    # ----------------------------------
    # 🔹 PERIOD relative
    # ----------------------------------
    if isinstance(period, dict):
        if period.get("type") == "relative_days":
            offset = int(period.get("offset", 0))
            target = today + timedelta(days=offset)
            print("✅ Resolved relative day:", target)
            return target, target + timedelta(days=1)

        if period.get("type") == "relative_weeks":
            offset = int(period.get("offset", 0))
            target = today + timedelta(weeks=offset)
            start = target - timedelta(days=target.weekday())
            print("✅ Resolved relative week:", start, "→", start + timedelta(days=7))
            return start, start + timedelta(days=7)

        if period.get("type") == "relative_months":
            offset = int(period.get("offset", 0))
            month = today.month - 1 + offset
            year = today.year + month // 12
            month = month % 12 + 1
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1)
            else:
                end = date(year, month + 1, 1)
            print("✅ Resolved relative month:", start, "→", end)
            return start, end

        if period.get("type") == "relative_years":
            offset = int(period.get("offset", 0))
            year = today.year + offset
            start = date(year, 1, 1)
            end = date(year + 1, 1, 1)
            print("✅ Resolved relative year:", start, "→", end)
            return start, end

    raise ValueError("Unknown period")
