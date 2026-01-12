from datetime import date, timedelta
import calendar
import re

from datetime import date, timedelta
import calendar
import unicodedata
import spacy

from nltk.stem.snowball import FrenchStemmer

_stemmer = FrenchStemmer()

nlp = spacy.load("fr_core_news_sm")


def period_to_dates(period):
    """
    Retourne une période (start, end)
    - start inclus
    - end EXCLUSIF

    `period` peut être :
    - un dict : { "offset": -X }  ← FORMAT OFFICIEL POUR LES SEMAINES
    - une string legacy (CURRENT_WEEK, PREVIOUS_WEEK, etc.)
    """

    today = date.today()

    # ======================================================
    # ✅ FORMAT OFFICIEL — SEMAINE RELATIVE PAR OFFSET
    # ======================================================
    if isinstance(period, dict):
        if "offset" not in period:
            raise ValueError(f"Période dict invalide : {period}")

        offset = int(period["offset"])
        week_start = today - timedelta(days=today.weekday())  # lundi
        start = week_start + timedelta(days=7 * offset)
        end = start + timedelta(days=7)
        return start, end

    # ======================================================
    # ⚠️ FORMAT STRING — COMPATIBILITÉ LEGACY UNIQUEMENT
    # ======================================================
    if not isinstance(period, str):
        raise ValueError(f"Période invalide : {period}")

    # ======================
    # 📆 SEMAINES (legacy)
    # ======================
    if period == "CURRENT_WEEK":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=7)
        return start, end

    if period == "PREVIOUS_WEEK":
        end = today - timedelta(days=today.weekday())
        start = end - timedelta(days=7)
        return start, end

    # ======================
    # 📆 MOIS
    # ======================
    if period == "CURRENT_MONTH":
        start = date(today.year, today.month, 1)
        days = calendar.monthrange(today.year, today.month)[1]
        return start, start + timedelta(days=days)

    if period == "PREVIOUS_MONTH":
        year = today.year if today.month > 1 else today.year - 1
        month = today.month - 1 if today.month > 1 else 12
        start = date(year, month, 1)
        days = calendar.monthrange(year, month)[1]
        return start, start + timedelta(days=days)

    # ======================
    # 📆 MOIS ABSOLU (MONTH_YYYY-MM)
    # ======================
    match = re.match(r"MONTH_(\d{4})-(\d{2})$", period)
    if match:
        year, month = map(int, match.groups())
        start = date(year, month, 1)
        days = calendar.monthrange(year, month)[1]
        return start, start + timedelta(days=days)

    # ======================
    # 📆 ANNÉES
    # ======================
    match = re.match(r"YEAR_(\d{4})$", period)
    if match:
        year = int(match.group(1))
        return date(year, 1, 1), date(year + 1, 1, 1)

    if period == "CURRENT_YEAR":
        return date(today.year, 1, 1), date(today.year + 1, 1, 1)

    if period == "PREVIOUS_YEAR":
        return date(today.year - 1, 1, 1), date(today.year, 1, 1)

    # ======================
    # ❌ ERREUR
    # ======================
    raise ValueError(f"Période inconnue : {period}")


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


def normalize_lemma(lemma: str) -> str:
    # féminin / pluriel simples
    if lemma.endswith("e"):
        lemma = lemma[:-1]
    if lemma.endswith("s"):
        lemma = lemma[:-1]
    return lemma


def lemmatize(text: str) -> list[str]:
    return [_stemmer.stem(w) for w in text.split() if len(w) > 2]


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


def format_period_for_display(start_iso: str, end_iso: str) -> tuple[str, str]:
    """
    start inclus
    end exclus → affichage end - 1 jour
    """
    start = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso) - timedelta(days=1)
    return start.isoformat(), end.isoformat()
