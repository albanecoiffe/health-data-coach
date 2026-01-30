from intent_based_querying.normalization.normalizer import normalize
import re
from datetime import date, timedelta
import calendar

from to_delete.agents.factual_agent import factual_response
from to_delete.agents.factual_agent import factual_response
from to_delete.agents.snapshot_agent import answer_with_snapshot
from to_delete.agents.small_talks_agent import answer_small_talk
from to_delete.agents.questions_agent import analyze_question
from to_delete.agents.summary_agent import summary_response
from to_delete.agents.recommendation_agent import recommendation_to_text
from to_delete.agents.coaching_agent import answer_coaching
from schemas.schemas import ChatRequest
from to_delete.periods import (
    period_to_dates,
    extract_year,
    resolve_period_from_decision,
)


from services.memory import add_to_memory, set_last_metric

from to_delete.comparisons import infer_period_context_from_keys
from fastapi import HTTPException

from sqlalchemy.orm import Session
from uuid import UUID


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
    # MARQUER LES BILANS SANS ÉCRASER LA PÉRIODE
    if is_summary and decision.get("type", "").startswith("REQUEST_"):
        return {
            **decision,
            "reply_mode": "SUMMARY",
        }

    has_last = re.search(r"\b(dernier|derniere|precedent|precedente)\b", msg)

    # ======================================================
    #  Recommandation
    # ======================================================
    if re.search(
        r"\b(recommande|recommandes|conseil|conseilles|que me recommande|que me recommandes|recommandations|recommandation)\b",
        msg,
    ):
        return {"type": "RECOMMENDATION"}

    # ======================================================
    # 🔥 COMPARAISON EXPLICITE
    # ======================================================
    if re.search(r"\b(plus|moins|autant|compare|compar[eé]|par rapport)\b", msg):
        # --- semaines ---
        if re.search(r"cette semaine", msg) and re.search(r"semaine derniere", msg):
            return {
                "type": "COMPARE_PERIODS",
                "metric": metric,
                "left": {"offset": 0},
                "right": {"offset": -1},
            }

        match_weeks = re.findall(r"il y a (\d+) semaines?", msg)
        if len(match_weeks) == 2:
            return {
                "type": "COMPARE_PERIODS",
                "metric": metric,
                "left": {"offset": -int(match_weeks[0])},
                "right": {"offset": -int(match_weeks[1])},
            }

        # --- mois ---
        if re.search(r"ce mois", msg) and re.search(r"mois dernier", msg):
            return {
                "type": "COMPARE_PERIODS",
                "metric": metric,
                "left": {"month_offset": 0},
                "right": {"month_offset": -1},
            }

    # ======================================================
    # 🔧 CORRECTION MÉTRIQUE ROBUSTE
    # ======================================================
    if re.search(r"\b(temp|temps|duree)\b", msg):
        decision = {**decision, "metric": "DURATION"}

    # ======================================================
    # 🔴 1️⃣ BILAN + ANNÉE EXPLICITE
    # ======================================================
    year = extract_year(msg)
    if (
        is_summary
        and year is not None
        and decision.get("type") not in {"REQUEST_MONTH", "REQUEST_WEEK"}
    ):
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
            "month_offset": -1 if has_last else 0,
            "metric": metric,
            "reply_mode": "SUMMARY",
        }

    # ======================================================
    # 🔴 4️⃣ BILAN + ANNÉE IMPLICITE
    # ======================================================
    if is_summary and re.search(r"\b(annee|année|an)\b", msg):
        return {
            "type": "REQUEST_YEAR_RELATIVE",
            "year_offset": -1 if has_last else 0,
            "metric": metric,
            "reply_mode": "SUMMARY",
        }

    # ======================================================
    # 🔒 5️⃣ DÉCISION LLM — ACCEPTÉE SI COHÉRENTE
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

    if re.search(r"\b(semaine derniere|semaine précédente|semaine d'avant)\b", msg):
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
        return {"type": "REQUEST_MONTH_RELATIVE", "month_offset": 0, "metric": metric}

    if re.search(r"\b(mois dernier|mois précédent)\b", msg):
        return {"type": "REQUEST_MONTH_RELATIVE", "month_offset": -1, "metric": metric}

    match = re.search(r"il y a (\d+) mois", msg)
    if match:
        return {
            "type": "REQUEST_MONTH_RELATIVE",
            "month_offset": -int(match.group(1)),
            "metric": metric,
        }

    # ======================================================
    # 🔴 8️⃣ MOIS NOMMÉ (UNIQUEMENT SI QUESTION OU ACTION)
    # ======================================================
    for month_name, month_num in MONTHS.items():
        if re.search(rf"\b{month_name}\b", msg):
            # ⚠️ on ne déclenche une requête que si
            # - le message est une QUESTION ou une ACTION implicite
            if decision.get("type") in {
                "REQUEST_WEEK",
                "REQUEST_MONTH",
                "REQUEST_MONTH_RELATIVE",
                "REQUEST_YEAR",
                "REQUEST_YEAR_RELATIVE",
                "COMPARE_PERIODS",
            }:
                return {
                    "type": "REQUEST_MONTH",
                    "month": month_num,
                    "year": extract_year(msg),
                    "metric": metric,
                }
            else:
                # contexte narratif → on laisse passer
                return decision

    # ======================================================
    # 🔴 9️⃣ ANNÉES (hors bilan)
    # ======================================================
    if re.search(r"\b(cette année|année en cours|cet an)\b", msg):
        return {"type": "REQUEST_YEAR_RELATIVE", "year_offset": 0, "metric": metric}

    if re.search(r"\b(année dernière|annee derniere|an dernier)\b", msg):
        return {"type": "REQUEST_YEAR_RELATIVE", "year_offset": -1, "metric": metric}

    if year is not None:
        return {"type": "REQUEST_YEAR", "year": year, "metric": metric}

    match = re.search(r"il y a (\d+) ans", msg)
    if match:
        return {
            "type": "REQUEST_YEAR_RELATIVE",
            "year_offset": -int(match.group(1)),
            "metric": metric,
        }

    # ======================================================
    # 🔵 🔟 BILAN SANS PÉRIODE
    # ======================================================
    if is_summary:
        return {"type": "SUMMARY"}

    # ======================================================
    # ⚪ FALLBACK
    # ======================================================
    return decision


from fastapi import HTTPException
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session


def route_decision(
    decision: dict,
    db: Session,
    user_id: UUID,
    message: str,
    session_id: str | None = None,
):
    metric = decision.get("metric", "DISTANCE")

    # ======================================================
    # 🟣 COMPARAISON DE PÉRIODES (PRIORITÉ ABSOLUE)
    # ======================================================
    if decision.get("type") == "COMPARE_PERIODS":
        return build_compare_request(decision, metric)

    # ======================================================
    # 🗨️ SMALL TALK / ANSWER_NOW SANS DONNÉES
    # ======================================================
    if decision.get("type") == "ANSWER_NOW":
        reply = answer_small_talk(message, session_id)

        if session_id:
            add_to_memory(session_id, "assistant", reply)

        return {
            "type": "ANSWER_NOW",
            "reply": reply,
        }

    # ======================================================
    # 📆 RÉSOLUTION DE LA PÉRIODE
    # ======================================================
    start, end = resolve_period_from_decision(decision, message)

    if start is None or end is None:
        raise HTTPException(status_code=400, detail="Période invalide")

    # ======================================================
    # 📊 RÉPONSE FACTUELLE (DB = SOURCE DE VÉRITÉ)
    # ======================================================
    reply = factual_response(
        db=db,
        user_id=user_id,
        start=start,
        end=end,
        metric=metric,
    )

    # ======================================================
    # 🧠 MÉMOIRE & CONTEXTE
    # ======================================================
    if session_id:
        add_to_memory(session_id, "assistant", reply)
        set_last_metric(session_id, metric)

    return {
        "type": "ANSWER_NOW",
        "reply": reply,
        "meta": {
            "metric": metric,
            "start": start.isoformat(),
            "end": end.isoformat(),
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
        "meta": {
            "metric": metric,
            "period_context": period_context,
            "left_label": "période 1",
            "right_label": "période 2",
        },
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


def has_word(msg: str, words: list[str]) -> bool:
    return any(re.search(rf"\b{w}\b", msg) for w in words)
