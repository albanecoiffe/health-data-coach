from datetime import date, timedelta
import calendar
import re

from datetime import date, timedelta
import calendar


def period_to_dates(period_key: str):
    """
    Retourne une période (start, end) avec la convention :
    - start inclus
    - end EXCLUSIF
    """
    today = date.today()

    # ======================
    # 📆 SEMAINES
    # ======================
    if period_key == "CURRENT_WEEK":
        start = today - timedelta(days=today.weekday())  # lundi
        end = start + timedelta(days=7)
        return start, end

    if period_key == "PREVIOUS_WEEK":
        end = today - timedelta(days=today.weekday())
        start = end - timedelta(days=7)
        return start, end

    # ======================
    # 📆 MOIS
    # ======================
    if period_key == "CURRENT_MONTH":
        start = date(today.year, today.month, 1)
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        end = start + timedelta(days=days_in_month)
        return start, end

    if period_key == "PREVIOUS_MONTH":
        if today.month == 1:
            year = today.year - 1
            month = 12
        else:
            year = today.year
            month = today.month - 1

        start = date(year, month, 1)
        days_in_month = calendar.monthrange(year, month)[1]
        end = start + timedelta(days=days_in_month)
        return start, end

    # ======================
    # 📆 PÉRIODES GLISSANTES
    # ======================
    if period_key == "LAST_2_WEEKS":
        end = today
        start = end - timedelta(days=14)
        return start, end

    if period_key == "PREVIOUS_2_WEEKS":
        end = today - timedelta(days=14)
        start = end - timedelta(days=14)
        return start, end

    # ======================
    # ❌ ERREUR
    # ======================
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
