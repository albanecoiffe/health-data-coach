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
    if decision.get("type") == "COMPARE_PERIODS":
        return decision

    is_summary = any(
        k in msg for k in ["bilan", "resume", "résumé", "recap", "synthese", "stat"]
    )

    for month_name, month_num in MONTHS.items():
        if re.search(rf"\b{month_name}\b", msg):
            return {
                "type": "SUMMARY" if is_summary else "REQUEST_MONTH",
                "month": month_num,
                "year": extract_year(msg),
                "metric": decision.get("metric") or "DISTANCE",
            }

    if is_summary:
        return {"type": "SUMMARY"}

    if re.search(r"\b(semaine)\b.*\b(precedente|derniere|davant)\b", msg) or re.search(
        r"\b(la\s+semaine)\s+(precedente|derniere)\b", msg
    ):
        return {
            "type": "REQUEST_WEEK",
            "offset": -1,
            "metric": decision.get("metric") or "DISTANCE",
        }

    return decision


def resolve_period_from_decision(
    decision: dict,
    message: str,
    snapshot_start_iso: str | None = None,
):
    today = date.today()
    msg = normalize(message)

    # ======================
    # 📆 SEMAINE
    # ======================
    if decision["type"] == "REQUEST_WEEK":
        offset = int(decision.get("offset", -1))
        week_start = today - timedelta(days=today.weekday())
        start = week_start + timedelta(days=7 * offset)
        end = start + timedelta(days=7)
        return start, end

    # ======================
    # 📆 MOIS / SUMMARY
    # ======================
    if decision["type"] in ["REQUEST_MONTH", "REQUEST_MONTH_RELATIVE", "SUMMARY"]:
        # 🔑 CAS CRITIQUE :
        # Si un snapshot mensuel est déjà fourni,
        # on l'utilise DIRECTEMENT comme vérité.
        if snapshot_start_iso:
            snapshot_start = date.fromisoformat(snapshot_start_iso)
            start = date(snapshot_start.year, snapshot_start.month, 1)
            days = calendar.monthrange(start.year, start.month)[1]
            end = start + timedelta(days=days)
            return start, end

        # 🔵 SINON : calcul normal depuis today
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

    return None, None


def snapshot_matches_period(snapshot, start: date, end: date) -> bool:
    return (
        snapshot.period.start == start.isoformat()
        and snapshot.period.end == end.isoformat()
    )


def route_decision(req: ChatRequest, decision: dict):
    decision_type = decision.get("type", "ANSWER_NOW")
    metric = decision.get("metric") or "DISTANCE"

    # ======================================================
    # 📆 PÉRIODES (SEMAINE / MOIS / SUMMARY)
    # ======================================================
    if decision_type in [
        "REQUEST_WEEK",
        "REQUEST_MONTH",
        "REQUEST_MONTH_RELATIVE",
        "SUMMARY",
    ]:
        # ⚠️ IMPORTANT :
        # snapshot_start_iso NE DOIT ÊTRE PASSÉ
        # QUE SI ON VEUT RÉPONDRE, PAS RECALCULER
        start, end = resolve_period_from_decision(
            decision,
            req.message,
            snapshot_start_iso=req.snapshot.period.start
            if decision_type != "REQUEST_MONTH_RELATIVE"
            else None,
        )

        if start and snapshot_matches_period(req.snapshot, start, end):
            if decision_type == "SUMMARY":
                return summary_response(req.snapshot)

            return factual_response(req.snapshot, metric)

        return {
            "type": "REQUEST_SNAPSHOT",
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "meta": {"metric": metric},
        }

    # ======================================================
    # 🔁 COMPARAISONS
    # ======================================================
    if decision_type == "COMPARE_PERIODS":
        return build_compare_request(decision, metric)

    # ======================================================
    # 📊 FACTUEL
    # ======================================================
    if decision.get("answer_mode") == "FACTUAL":
        return factual_response(req.snapshot, metric)

    # ======================================================
    # 💬 FALLBACK
    # ======================================================
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
