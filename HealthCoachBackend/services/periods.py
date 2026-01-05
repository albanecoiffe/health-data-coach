from datetime import date, timedelta
import calendar


def period_to_dates(period_key: str):
    today = date.today()

    if period_key == "CURRENT_WEEK":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=7)
        return start, end

    if period_key == "PREVIOUS_WEEK":
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=7)
        return start, end

    if period_key == "CURRENT_MONTH":
        start = date(today.year, today.month, 1)
        end = date(
            today.year, today.month, calendar.monthrange(today.year, today.month)[1]
        )
        return start, end

    if period_key == "PREVIOUS_MONTH":
        month = today.month - 1 or 12
        year = today.year - 1 if today.month == 1 else today.year
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        return start, end

    if period_key == "LAST_2_WEEKS":
        end = today
        start = today - timedelta(days=14)
        return start, end

    if period_key == "PREVIOUS_2_WEEKS":
        end = today - timedelta(days=14)
        start = end - timedelta(days=14)
        return start, end

    raise ValueError(f"Période inconnue : {period_key}")


import unicodedata


def normalize(text: str) -> str:
    text = text.lower()

    # Normalisation Unicode (séparation accents)
    text = unicodedata.normalize("NFD", text)

    # Suppression des accents
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")

    # Normalisation des apostrophes et guillemets
    text = text.replace("’", "'")
    text = text.replace("‘", "'")
    text = text.replace("`", "'")
    text = text.replace("´", "'")

    # Optionnel mais recommandé : tirets typographiques → tiret simple
    text = text.replace("–", "-").replace("—", "-")

    return text


def resolve_period(message: str, snapshot_period: tuple[str, str]):
    msg = normalize(message)
    today = date.today()

    # === SEMAINES ===
    if "semaine derniere" in msg or "semaine precedente" in msg:
        return period_to_dates("PREVIOUS_WEEK")

    if "cette semaine" in msg or "semaine actuelle" in msg:
        return period_to_dates("CURRENT_WEEK")

    # === MOIS ===
    if "mois dernier" in msg:
        return period_to_dates("PREVIOUS_MONTH")

    if "ce mois" in msg or "ce mois ci" in msg:
        return period_to_dates("CURRENT_MONTH")

    # === FALLBACK → période courante
    start, end = snapshot_period
    return date.fromisoformat(start), date.fromisoformat(end)
