# "hier", "7 derniers jours", etc. -> (start,end)

# time_resolver.py
from datetime import datetime, date, timedelta
from typing import Tuple
import re
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


def resolve_period(period):
    today = date.today()
    print("\n🕒 TIME RESOLUTION")
    print("➡️ Period keyword :", period)

    # --------------------------------------------------
    # 1️⃣ STRUCTURED PERIODS (dict) — ALWAYS FIRST
    # --------------------------------------------------
    if isinstance(period, dict):
        if period.get("type") == "named_month":
            month = int(period["month"])
            year = period.get("year")

            if year is None:
                # mois le plus récent dans le passé
                if month > today.month:
                    year = today.year - 1
                else:
                    year = today.year

            start = date(year, month, 1)

            if month == 12:
                end = date(year + 1, 1, 1)
            else:
                end = date(year, month + 1, 1)

            print("✅ Resolved named month:", start, "→", end)
            return start, end

        if period.get("type") == "named_year":
            year = int(period["year"])
            start = date(year, 1, 1)
            end = date(year + 1, 1, 1)
            print("✅ Resolved named year:", start, "→", end)
            return start, end

        raise ValueError(f"Unknown structured period: {period}")

    # --------------------------------------------------
    # 2️⃣ STRING-BASED PERIODS
    # --------------------------------------------------
    if not isinstance(period, str):
        raise TypeError(f"period must be str or dict, got {type(period)}")

    if period == "today":
        return today, today + timedelta(days=1)

    if period == "yesterday":
        y = today - timedelta(days=1)
        return y, today

    if period == "this_week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=7)

    if period == "last_week":
        end = today - timedelta(days=today.weekday())
        start = end - timedelta(days=7)
        return start, end

    if period == "this_month":
        start = today.replace(day=1)
        end = (
            start.replace(year=start.year + 1, month=1)
            if start.month == 12
            else start.replace(month=start.month + 1)
        )
        return start, end

    if period == "this_year":
        start = date(today.year, 1, 1)
        end = date(today.year + 1, 1, 1)
        return start, end

    if period == "last_month":
        first = today.replace(day=1)
        end = first
        start = (
            first.replace(year=first.year - 1, month=12)
            if first.month == 1
            else first.replace(month=first.month - 1)
        )
        return start, end

    # --------------------------------------------------
    # 3️⃣ DYNAMIC RELATIVE DAYS (last_X_days)
    # --------------------------------------------------
    m = re.match(r"last_(\d+)_days", period)
    if m:
        days = int(m.group(1))
        return today - timedelta(days=days), today

    m = re.match(r"last_(\d+)_weeks", period)
    if m:
        weeks = int(m.group(1))
        end = today - timedelta(days=today.weekday())
        start = end - timedelta(weeks=weeks)
        return start, end

    m = re.match(r"last_(\d+)_months", period)
    if m:
        months = int(m.group(1))
        first = today.replace(day=1)
        end = first
        month = first.month - months
        year = first.year
        while month <= 0:
            month += 12
            year -= 1
        start = first.replace(year=year, month=month)
        return start, end

    m = re.match(r"last_(\d+)_years", period)
    if m:
        years = int(m.group(1))
        first = today.replace(month=1, day=1)
        end = first
        start = first.replace(year=first.year - years)
        return start, end

    raise ValueError(f"Unknown period: {period}")


def normalize_period_with_original_message(period, original_message: str):
    # 🛑 SI la période est déjà explicite → on ne touche à rien
    if isinstance(period, str) and period not in {"this_month", "this_year"}:
        return period

    msg = original_message.lower()

    months = {
        "janvier": 1,
        "février": 2,
        "mars": 3,
        "avril": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7,
        "août": 8,
        "septembre": 9,
        "octobre": 10,
        "novembre": 11,
        "décembre": 12,
    }

    found_month = None
    for name, month in months.items():
        if name in msg:
            found_month = month
            break

    year_match = re.search(r"\b(19|20)\d{2}\b", msg)
    found_year = int(year_match.group()) if year_match else None

    # 🔹 Mois nommé
    if found_month is not None:
        return {
            "type": "named_month",
            "month": found_month,
            "year": found_year,
        }

    # 🔹 ANNÉE NOMMÉE (🔥 MANQUANT 🔥)
    if found_year is not None:
        return {
            "type": "named_year",
            "year": found_year,
        }

    return period


def serialize_period(period) -> str:
    if isinstance(period, dict):
        if period.get("type") == "named_year":
            return str(period["year"])
        if period.get("type") == "named_month":
            return f"{period['year']}-{period['month']:02d}"
    return str(period)
