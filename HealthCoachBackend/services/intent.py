from services.periods import normalize
import re
from datetime import date, timedelta
import calendar
from agent import factual_response, summary_response, answer_with_snapshot
from schemas import ChatRequest
from services.periods import period_to_dates
from services.comparisons import infer_period_context_from_keys
from fastapi import HTTPException

LABELS = {
    "CURRENT_WEEK": "cette semaine",
    "PREVIOUS_WEEK": "la semaine dernière",
    "CURRENT_MONTH": "ce mois-ci",
    "PREVIOUS_MONTH": "le mois dernier",
}

MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
}


def apply_backend_overrides(message: str, decision: dict) -> dict:
    msg = normalize(message)

    # 🔒 VERROU ABSOLU : décisions temporelles intouchables
    if decision.get("type") in {
        "REQUEST_WEEK",
        "REQUEST_MONTH",
        "REQUEST_MONTH_RELATIVE",
        "REQUEST_YEAR",
        "REQUEST_YEAR_RELATIVE",
        "COMPARE_PERIODS",
    }:
        return decision

    # 🔴 Comparaisons : intouchables
    if decision.get("type") == "COMPARE_PERIODS":
        return decision

    is_summary = any(
        k in msg
        for k in [
            "bilan",
            "resume",
            "résumé",
            "recap",
            "synthese",
            "stat",
            "statistiques",
        ]
    )

    # ======================================================
    # PRIORITÉ ABSOLUE — MOIS EXPLICITE
    # ======================================================
    for month_name, month_num in MONTHS.items():
        if re.search(rf"\b{month_name}\b", msg):
            return {
                "type": "REQUEST_MONTH",
                "month": month_num,
                "year": extract_year(msg),
                "metric": decision.get("metric") or "DISTANCE",
            }

    # ======================================================
    # ANNÉE RELATIVE (cette année, l’an dernier, etc.)
    # ======================================================
    if is_summary:
        if any(
            k in msg
            for k in [
                "cette annee",
                "cette année",
                "année en cours",
                "annee en cours",
                "cet an",
                "an en cours",
            ]
        ):
            return {
                "type": "REQUEST_YEAR_RELATIVE",
                "offset": 0,
            }

        if any(
            k in msg
            for k in [
                "annee derniere",
                "année dernière",
                "an dernier",
                "annee precedente",
                "année précédente",
                "an precedente",
                "an précédente",
            ]
        ):
            return {
                "type": "REQUEST_YEAR_RELATIVE",
                "offset": -1,
            }

    # ======================================================
    # 3️⃣ ANNÉE EXPLICITE (2025, 2024…)
    # ======================================================
    if is_summary:
        year = extract_year(msg)
        if year is not None:
            return {
                "type": "REQUEST_YEAR",
                "year": year,
            }

    # ======================================================
    # semaine
    # ======================================================
    if decision.get("type") == "SUMMARY":
        # "il y a X semaines"
        match = re.search(r"il y a (\d+) semaines?", msg)
        if match:
            offset = -int(match.group(1))
            return {
                "type": "REQUEST_WEEK",
                "offset": offset,
            }

        # "semaine dernière"
        if (
            "semaine derniere" in msg
            or "semaine dernière" in msg
            or "la semaine derniere" in msg
            or "la semaine dernière" in msg
            or "semaine d'avant" in msg
            or "la semaine d'avant" in msg
            or "semaine précédente" in msg
            or "la semaine précédente" in msg
        ):
            return {
                "type": "REQUEST_WEEK",
                "offset": -1,
            }

        # "cette semaine"
        if "cette semaine" in msg:
            return {
                "type": "REQUEST_WEEK",
                "offset": 0,
            }
    # ======================================================
    # 4️⃣ BILAN SANS PÉRIODE → PÉRIODE COURANTE
    # ======================================================
    if is_summary:
        return {"type": "SUMMARY"}

    # ======================================================
    # 5️⃣ SEMAINE PRÉCÉDENTE
    # ======================================================
    if re.search(r"\b(semaine)\b.*\b(precedente|derniere|davant)\b", msg):
        return {
            "type": "REQUEST_WEEK",
            "offset": -1,
            "metric": decision.get("metric") or "DISTANCE",
        }

    return decision


def resolve_period_from_decision(decision: dict, message: str):
    """
    Retourne (start, end) avec convention :
    - start inclus
    - end exclusif
    """
    today = date.today()
    msg = normalize(message)
    decision_type = decision.get("type")

    # ======================
    # 📆 SEMAINES
    # ======================
    if decision_type == "REQUEST_WEEK":
        offset = int(decision.get("offset", 0))
        week_start = today - timedelta(days=today.weekday())  # lundi
        start = week_start + timedelta(days=7 * offset)
        end = start + timedelta(days=7)
        return start, end

    # ======================
    # 📆 MOIS ABSOLU (EX: septembre 2025)
    # ======================
    if decision_type == "REQUEST_MONTH":
        month = int(decision["month"])
        raw_year = decision.get("year")

        if raw_year is not None:
            year = int(raw_year)
        else:
            # si pas d'année : on déduit (mois passé le plus probable)
            year = today.year if month < today.month else today.year - 1

        start = date(year, month, 1)
        days = calendar.monthrange(year, month)[1]
        end = start + timedelta(days=days)
        return start, end

    # ======================
    # 📆 MOIS RELATIF (mois dernier, il y a X mois, etc.)
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
    # 📆 ANNÉE ABSOLUE / RELATIVE (si tu l’ajoutes)
    # ======================
    if decision_type == "REQUEST_YEAR":
        year = int(decision["year"])
        return date(year, 1, 1), date(year + 1, 1, 1)

    if decision_type == "REQUEST_YEAR_RELATIVE":
        offset = int(decision.get("offset", -1))
        year = today.year + offset
        return date(year, 1, 1), date(year + 1, 1, 1)

    # ======================
    # SUMMARY sans période explicite = période courante (pas ici)
    # ======================
    return None, None


def snapshot_matches_period(snapshot, start: date, end: date) -> bool:
    return (
        snapshot.period.start == start.isoformat()
        and snapshot.period.end == end.isoformat()
    )


def route_decision(req: ChatRequest, decision: dict):
    decision_type = decision.get("type")
    metric = decision.get("metric") or "DISTANCE"

    msg = normalize(req.message)
    wants_summary = any(
        k in msg for k in ["bilan", "resume", "résumé", "recap", "synthese", "stat"]
    )

    # 🔴 Année (si snapshot correspond : summary)
    if decision_type in ["REQUEST_YEAR", "REQUEST_YEAR_RELATIVE"]:
        start, end = resolve_period_from_decision(decision, req.message)

        if snapshot_matches_period(req.snapshot, start, end):
            return summary_response(req.snapshot)

        return {
            "type": "REQUEST_SNAPSHOT",
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
        }

    # 🔵 SUMMARY "pur" = période courante UNIQUEMENT
    if decision_type == "SUMMARY":
        return summary_response(req.snapshot)

    # 🟡 mois / semaines
    if decision_type in ["REQUEST_WEEK", "REQUEST_MONTH", "REQUEST_MONTH_RELATIVE"]:
        start, end = resolve_period_from_decision(decision, req.message)

        if snapshot_matches_period(req.snapshot, start, end):
            # ✅ si l’utilisateur a demandé un bilan, on renvoie le summary
            if wants_summary:
                return summary_response(req.snapshot)
            return factual_response(req.snapshot, metric)

        return {
            "type": "REQUEST_SNAPSHOT",
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "meta": {"metric": metric},
        }

    # Comparaison
    if decision_type == "COMPARE_PERIODS":
        return build_compare_request(decision, metric)

    # Fallback
    if decision.get("answer_mode") == "FACTUAL":
        return factual_response(req.snapshot, metric)

    return {"reply": answer_with_snapshot(req.message, req.snapshot)}


def build_compare_request(decision: dict, metric: str):
    """
    Construit une requête REQUEST_SNAPSHOT_BATCH
    à partir d'une décision COMPARE_PERIODS
    """

    left_key = decision["left"]
    right_key = decision["right"]

    # 🔑 Contexte temporel (WEEK / MONTH / YEAR / None)
    period_context = infer_period_context_from_keys(left_key)

    # 📅 Résolution des périodes
    left_start, left_end = period_to_dates(left_key)
    right_start, right_end = period_to_dates(right_key)

    meta = {
        "metric": metric,
        "left_label": LABELS.get(left_key, "période 1"),
        "right_label": LABELS.get(right_key, "période 2"),
    }

    if period_context is not None:
        meta["period_context"] = period_context

    return {
        "type": "REQUEST_SNAPSHOT_BATCH",
        "snapshots": {
            "left": {
                "start": left_start.isoformat(),
                "end": left_end.isoformat(),
            },
            "right": {
                "start": right_start.isoformat(),
                "end": right_end.isoformat(),
            },
        },
        "meta": meta,
    }


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
