from datetime import date, timedelta
import calendar
import re

from datetime import date, timedelta
import calendar
import unicodedata


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
    # 📆 MOIS ABSOLUS (ex: MONTH_2025-09)
    # ======================
    match = re.match(r"MONTH_(\d{4})-(\d{2})$", period_key)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))

        if month < 1 or month > 12:
            raise ValueError(f"Mois invalide : {period_key}")

        start = date(year, month, 1)
        days_in_month = calendar.monthrange(year, month)[1]
        end = start + timedelta(days=days_in_month)
        return start, end

    # ======================
    # 📆 MOIS ISO (YYYY-MM)
    # ======================
    match = re.match(r"^(\d{4})-(\d{2})$", period_key)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))

        if month < 1 or month > 12:
            raise ValueError(f"Mois invalide : {period_key}")

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
    # 📆 ANNÉES ABSOLUES
    # ======================
    match = re.match(r"YEAR_(\d{4})$", period_key)
    if match:
        year = int(match.group(1))
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
        return start, end

    # ======================
    # 📆 ANNÉES RELATIVES
    # ======================
    if period_key == "CURRENT_YEAR":
        year = today.year
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
        return start, end

    if period_key == "PREVIOUS_YEAR":
        year = today.year - 1
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
        return start, end

    # ======================
    # ❌ ERREUR
    # ======================
    raise ValueError(f"Période inconnue : {period_key}")


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


def snapshot_matches_iso(snapshot, start_iso: str, end_iso: str) -> bool:
    """
    Vérifie que le snapshot correspond exactement à la période demandée.
    On compare des strings ISO (yyyy-mm-dd) → simple et fiable.
    """
    return snapshot.period.start == start_iso and snapshot.period.end == end_iso


def extract_year(message: str) -> int | None:
    """
    Extrait une année (YYYY) du message utilisateur.
    Retourne None si aucune année explicite n'est trouvée.
    """
    current_year = date.today().year

    match = re.search(r"\b(19|20)\d{2}\b", message)
    if not match:
        return None

    year = int(match.group())

    # garde-fou simple : pas d'année absurde
    if year < 2000 or year > current_year + 1:
        return None

    return year


def snapshot_matches_period(snapshot, start: date, end: date) -> bool:
    """
    Vérifie que le snapshot correspond EXACTEMENT
    à la période [start, end[ (end exclusif).
    """
    return (
        snapshot.period.start == start.isoformat()
        and snapshot.period.end == end.isoformat()
    )


def resolve_period_from_decision(decision: dict, message: str):
    """
    Résout une décision temporelle en (start, end)
    Convention :
    - start inclus
    - end exclusif
    """
    today = date.today()
    decision_type = decision.get("type")

    # ======================
    # 📆 SEMAINE
    # ======================
    if decision_type == "REQUEST_WEEK":
        offset = int(decision.get("offset", 0))
        week_start = today - timedelta(days=today.weekday())  # lundi
        start = week_start + timedelta(days=7 * offset)
        end = start + timedelta(days=7)
        return start, end

    # ======================
    # 📆 MOIS ABSOLU (ex: novembre 2025)
    # ======================
    if decision_type == "REQUEST_MONTH":
        month = int(decision["month"])
        raw_year = decision.get("year")

        # 🔑 L'année n'est fiable QUE si l'utilisateur l'a explicitement donnée
        user_year = extract_year(message)

        if user_year is not None:
            year = user_year
        else:
            # heuristique : dernier mois plausible dans le passé
            year = today.year if month < today.month else today.year - 1

        start = date(year, month, 1)
        days = calendar.monthrange(year, month)[1]
        end = start + timedelta(days=days)
        return start, end

    # ======================
    # 📆 MOIS RELATIF (ce mois, mois dernier, il y a X mois)
    # ======================
    if decision_type == "REQUEST_MONTH_RELATIVE":
        offset = int(decision.get("offset", 0))
        target_month = today.month + offset
        target_year = today.year

        while target_month < 1:
            target_month += 12
            target_year -= 1
        while target_month > 12:
            target_month -= 12
            target_year += 1

        start = date(target_year, target_month, 1)
        days = calendar.monthrange(target_year, target_month)[1]
        end = start + timedelta(days=days)
        return start, end

    # ======================
    # 📆 ANNÉE ABSOLUE
    # ======================
    if decision_type == "REQUEST_YEAR":
        year = int(decision["year"])
        return date(year, 1, 1), date(year + 1, 1, 1)

    # ======================
    # 📆 ANNÉE RELATIVE
    # ======================
    if decision_type == "REQUEST_YEAR_RELATIVE":
        offset = int(decision.get("offset", 0))
        year = today.year + offset
        return date(year, 1, 1), date(year + 1, 1, 1)

    # ======================
    # ❌ Aucune période
    # ======================
    return None, None
