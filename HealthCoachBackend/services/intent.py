from services.periods import normalize
import re
from datetime import date, timedelta
import calendar
from agent import factual_response, summary_response, answer_with_snapshot
from schemas import ChatRequest


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


def resolve_period_from_decision(decision: dict, message: str):
    today = date.today()
    msg = normalize(message)

    if decision["type"] == "REQUEST_WEEK":
        offset = int(decision.get("offset", -1))
        week_start = today - timedelta(days=today.weekday())
        start = week_start + timedelta(days=7 * offset)
        end = start + timedelta(days=7)
        return start, end

    if decision["type"] in ["REQUEST_MONTH", "REQUEST_MONTH_RELATIVE", "SUMMARY"]:
        offset = 0

        if "mois dernier" in msg:
            offset = -1
        elif "ce mois" in msg:
            offset = 0
        elif decision.get("month"):
            month = decision["month"]
            raw_year = decision.get("year")

            if raw_year:
                year = raw_year
            else:
                # dernier mois écoulé
                if month < today.month:
                    year = today.year
                else:
                    year = today.year - 1

            start = date(year, month, 1)
            days = calendar.monthrange(year, month)[1]
            end = start + timedelta(days=days)
            return start, end

        # mois relatif
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

    if decision_type in [
        "REQUEST_WEEK",
        "REQUEST_MONTH",
        "REQUEST_MONTH_RELATIVE",
        "SUMMARY",
    ]:
        start, end = resolve_period_from_decision(decision, req.message)

        if start and snapshot_matches_period(req.snapshot, start, end):
            if decision_type == "SUMMARY":
                return summary_response(req.snapshot)
            return factual_response(req.snapshot, metric)

        return {
            "type": "REQUEST_SNAPSHOT",
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "meta": {"metric": metric},
        }

    if decision_type == "COMPARE_PERIODS":
        return build_compare_request(decision, metric)

    if decision.get("answer_mode") == "FACTUAL":
        return factual_response(req.snapshot, metric)

    return {"reply": answer_with_snapshot(req.message, req.snapshot)}


from services.periods import period_to_dates

LABELS = {
    "CURRENT_WEEK": "cette semaine",
    "PREVIOUS_WEEK": "la semaine dernière",
    "CURRENT_MONTH": "ce mois-ci",
    "PREVIOUS_MONTH": "le mois dernier",
}


def build_compare_request(decision: dict, metric: str):
    """
    Construit une requête REQUEST_SNAPSHOT_BATCH
    à partir d'une décision COMPARE_PERIODS
    """

    left_key = decision["left"]
    right_key = decision["right"]

    left_start, left_end = period_to_dates(left_key)
    right_start, right_end = period_to_dates(right_key)

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
        "meta": {
            "metric": metric,
            "left_label": LABELS.get(left_key, "période 1"),
            "right_label": LABELS.get(right_key, "période 2"),
        },
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
