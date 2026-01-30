from datetime import date, timedelta
import calendar
import re
import unicodedata
import spacy

from nltk.stem.snowball import FrenchStemmer

_stemmer = FrenchStemmer()

nlp = spacy.load("fr_core_news_sm")


def period_to_dates(period):
    """
    Transformer UNE clé de période (left ou right) en dates.
    input : clé de période {"offset": -1} ou {"month_offset": 0}
    output : (start: date, end: date)
    """
    today = date.today()

    # ======================
    # 📆 RELATIF — SEMAINE
    # ======================
    if isinstance(period, dict) and "offset" in period:
        offset = int(period["offset"])
        week_start = today - timedelta(days=today.weekday())
        start = week_start + timedelta(days=7 * offset)
        return start, start + timedelta(days=7)

    # ======================
    # 📆 RELATIF — MOIS
    # ======================
    if isinstance(period, dict) and "month_offset" in period:
        offset = int(period["month_offset"])
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
        return start, start + timedelta(days=days)

    # ======================
    # 📆 RELATIF — ANNÉE
    # ======================
    if isinstance(period, dict) and "year_offset" in period:
        offset = int(period["year_offset"])
        year = today.year + offset
        return date(year, 1, 1), date(year + 1, 1, 1)

    # ======================
    # 📆 ABSOLU — MOIS (AUTORISÉ)
    # ======================
    if isinstance(period, str):
        match = re.match(r"MONTH_(\d{4})-(\d{2})$", period)
        if match:
            year, month = map(int, match.groups())
            start = date(year, month, 1)
            days = calendar.monthrange(year, month)[1]
            return start, start + timedelta(days=days)

    # ======================
    # ❌ ERREUR
    # ======================
    raise ValueError(f"Période inconnue : {period}")


def resolve_period_from_decision(decision: dict, message: str):
    """
    Transformer UNE décision LLM du type : { "type": "REQUEST_WEEK", "offset": -1 }
    en UNE période concrète : (start: date, end: date)
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
            # dernier mois plausible dans le passé
            # si le mois est supérieur au mois actuel, on prend l'année précédente
            # si non, l'année en cours
            # si le mois est egale au mois actuel, on prend l'année en cours

            year = today.year if month <= today.month else today.year - 1

        start = date(year, month, 1)
        days = calendar.monthrange(year, month)[1]
        end = start + timedelta(days=days)
        return start, end

    # ======================
    # 📆 MOIS RELATIF (ce mois, mois dernier, il y a X mois)
    # ======================
    if decision_type == "REQUEST_MONTH_RELATIVE":
        offset = int(decision.get("month_offset", 0))
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
        offset = int(decision.get("year_offset", 0))
        year = today.year + offset
        return date(year, 1, 1), date(year + 1, 1, 1)

    # ======================
    # ❌ Aucune période
    # ======================
    return None, None


def format_period_for_display(start_iso: str, end_iso: str) -> tuple[str, str]:
    """
    start inclus
    end exclus → affichage end - 1 jour
    """
    start = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def normalize_lemma(lemma: str) -> str:
    # féminin / pluriel simples
    if lemma.endswith("e"):
        lemma = lemma[:-1]
    if lemma.endswith("s"):
        lemma = lemma[:-1]
    return lemma


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


from datetime import datetime, timedelta


def get_current_week_interval():
    now = datetime.utcnow()
    start = now - timedelta(days=now.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return start, end
