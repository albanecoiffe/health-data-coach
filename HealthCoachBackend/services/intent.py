from services.periods import normalize
import re
from datetime import date, timedelta
import calendar
from agent import factual_response, summary_response, answer_with_snapshot
from schemas import ChatRequest
from services.periods import (
    period_to_dates,
    extract_year,
    snapshot_matches_period,
    resolve_period_from_decision,
)
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
    metric = decision.get("metric", "DISTANCE")

    is_summary = re.search(r"\b(bilan|resume|recap|synthese|stat)\b", msg)
    has_last = re.search(r"\b(dernier|derniere|precedent|precedente)\b", msg)

    # ======================================================
    # 🔧 CORRECTION MÉTRIQUE ROBUSTE (typos fréquentes)
    # ======================================================
    if re.search(r"\b(temp|temps|duree)\b", msg):
        decision = {**decision, "metric": "DURATION"}

    # ======================================================
    # 🔴 1️⃣ BILAN + ANNÉE EXPLICITE (PRIORITÉ ABSOLUE)
    # ======================================================
    year = extract_year(msg)
    if is_summary and year is not None:
        return {
            "type": "REQUEST_YEAR",
            "year": year,
            "metric": metric,
            "reply_mode": "SUMMARY",
        }

    # ======================================================
    # 🔴 2️⃣ BILAN + SEMAINE
    # ======================================================
    if is_summary and re.search(r"\b(semaine)\b", msg):
        return {
            "type": "REQUEST_WEEK",
            "offset": -1 if has_last else 0,
            "metric": metric,
            "reply_mode": "SUMMARY",
        }

    # ======================================================
    # 🔴 3️⃣ BILAN + MOIS
    # ======================================================
    if is_summary and re.search(r"\b(mois)\b", msg):
        return {
            "type": "REQUEST_MONTH_RELATIVE",
            "offset": -1 if has_last else 0,
            "metric": metric,
            "reply_mode": "SUMMARY",
        }

    # ======================================================
    # 🔴 4️⃣ BILAN + ANNÉE IMPLICITE
    # ======================================================
    if is_summary and re.search(r"\b(annee|année|an)\b", msg):
        return {
            "type": "REQUEST_YEAR_RELATIVE",
            "offset": -1 if has_last else 0,
            "metric": metric,
            "reply_mode": "SUMMARY",
        }

    # ======================================================
    # 🔒 5️⃣ DÉCISION TEMPORELLE LLM → intouchable
    # ======================================================
    if decision.get("type") in {
        "REQUEST_WEEK",
        "REQUEST_MONTH",
        "REQUEST_MONTH_RELATIVE",
        "REQUEST_YEAR",
        "REQUEST_YEAR_RELATIVE",
        "COMPARE_PERIODS",
    }:
        return decision

    # ======================================================
    # 🔴 6️⃣ SEMAINE (hors bilan)
    # ======================================================
    if re.search(r"\b(cette semaine|semaine en cours)\b", msg):
        return {"type": "REQUEST_WEEK", "offset": 0, "metric": metric}

    if re.search(
        r"\b(semaine derniere|semaine dernière|semaine precedente|semaine précédente|semaine d'avant)\b",
        msg,
    ):
        return {"type": "REQUEST_WEEK", "offset": -1, "metric": metric}

    match = re.search(r"il y a (\d+) semaines?", msg)
    if match:
        return {
            "type": "REQUEST_WEEK",
            "offset": -int(match.group(1)),
            "metric": metric,
        }

    # ======================================================
    # 🔴 7️⃣ MOIS RELATIFS (hors bilan)
    # ======================================================
    if re.search(r"\b(ce mois|ce mois-ci|mois en cours)\b", msg):
        return {"type": "REQUEST_MONTH_RELATIVE", "offset": 0, "metric": metric}

    if re.search(r"\b(mois dernier|mois precedent|mois précédente)\b", msg):
        return {"type": "REQUEST_MONTH_RELATIVE", "offset": -1, "metric": metric}

    match = re.search(r"il y a (\d+) mois", msg)
    if match:
        return {
            "type": "REQUEST_MONTH_RELATIVE",
            "offset": -int(match.group(1)),
            "metric": metric,
        }

    # ======================================================
    # 🔴 8️⃣ MOIS NOMMÉ (novembre, mars…)
    # ======================================================
    for month_name, month_num in MONTHS.items():
        if re.search(rf"\b{month_name}\b", msg):
            return {
                "type": "REQUEST_MONTH",
                "month": month_num,
                "year": extract_year(msg),
                "metric": metric,
            }

    # ======================================================
    # 🔴 9️⃣ ANNÉES (hors bilan)
    # ======================================================
    if re.search(r"\b(cette année|année en cours|cet an)\b", msg):
        return {"type": "REQUEST_YEAR_RELATIVE", "offset": 0, "metric": metric}

    if re.search(
        r"\b(année dernière|annee derniere|an dernier|année précédente)\b", msg
    ):
        return {"type": "REQUEST_YEAR_RELATIVE", "offset": -1, "metric": metric}

    if year is not None:
        return {"type": "REQUEST_YEAR", "year": year, "metric": metric}

    match = re.search(r"il y a (\d+) ans", msg)
    if match:
        return {
            "type": "REQUEST_YEAR_RELATIVE",
            "offset": -int(match.group(1)),
            "metric": metric,
        }

    # ======================================================
    # 🔵 🔟 BILAN SANS PÉRIODE → période courante
    # ======================================================
    if is_summary:
        return {"type": "SUMMARY"}

    # ======================================================
    # ⚪ FALLBACK → décision LLM
    # ======================================================
    return decision


def route_decision(req: ChatRequest, decision: dict):
    meta = req.meta or {}
    session_id = meta.get("session_id", "default")
    metric = decision.get("metric", "DISTANCE")

    # ======================================================
    # 🛑 ANSWER_NOW → réponse immédiate
    # ======================================================
    if decision.get("type") == "ANSWER_NOW":
        answer_mode = decision.get("answer_mode", "FACTUAL")

        if answer_mode == "FACTUAL":
            return {
                "type": "ANSWER_NOW",
                "reply": factual_response(req.snapshot, metric)["reply"],
            }

        return {
            "type": "ANSWER_NOW",
            "reply": answer_with_snapshot(req.message, req.snapshot, session_id),
        }

    # ======================================================
    # 📆 RÉSOLUTION PÉRIODE
    # ======================================================
    decision_type = decision.get("type")
    start, end = resolve_period_from_decision(decision, req.message)

    if start is None or end is None:
        raise HTTPException(status_code=400, detail="Période invalide")

    # ======================================================
    # ✅ SNAPSHOT MATCH → réponse directe
    # ======================================================
    reply_mode = decision.get("reply_mode", "FACTUAL")

    if reply_mode == "SUMMARY":
        reply = summary_response(req.snapshot)["reply"]
    else:
        reply = factual_response(req.snapshot, metric)["reply"]

    # ======================================================
    # 📤 SNAPSHOT MANQUANT
    # ======================================================
    reply_mode = decision.get("reply_mode", "FACTUAL")
    return {
        "type": "REQUEST_SNAPSHOT",
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "meta": {
            "metric": metric,
            "reply_mode": reply_mode,
            "requested_start": start.isoformat(),
            "requested_end": end.isoformat(),
        },
    }


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


def compute_intensity_split(snapshot):
    zones = getattr(snapshot, "zones_percent", None)
    if not isinstance(zones, dict):
        return None

    low = zones.get("z1", 0) + zones.get("z2", 0) + zones.get("z3", 0)
    high = zones.get("z4", 0) + zones.get("z5", 0)

    total = low + high
    if total == 0:
        return None

    return {
        "low_pct": round(low * 100, 1),
        "high_pct": round(high * 100, 1),
    }


import re


def has_word(msg: str, words: list[str]) -> bool:
    return any(re.search(rf"\b{w}\b", msg) for w in words)
