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

    # 🛑 SI LE LLM A DÉCIDÉ ANSWER_NOW → ON N'ÉCRASE JAMAIS
    if decision.get("type") == "ANSWER_NOW":
        return decision

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

    # ======================================================
    # 🔴 SEMAINE — PRIORITÉ ABSOLUE
    # ======================================================
    if any(
        k in msg
        for k in [
            "cette semaine",
            "semaine en cours",
        ]
    ):
        return {
            "type": "REQUEST_WEEK",
            "offset": 0,
            "metric": decision.get("metric") or "DISTANCE",
        }

    match = re.search(r"il y a (\d+) semaines?", msg)
    if match:
        return {
            "type": "REQUEST_WEEK",
            "offset": -int(match.group(1)),
            "metric": decision.get("metric") or "DISTANCE",
        }

    if any(
        k in msg
        for k in [
            "semaine derniere",
            "semaine dernière",
            "la semaine derniere",
            "la semaine dernière",
            "semaine precedente",
            "semaine précédente",
            "semaine d'avant",
        ]
    ):
        return {
            "type": "REQUEST_WEEK",
            "offset": -1,
            "metric": decision.get("metric") or "DISTANCE",
        }

    # ======================================================
    # 🔴 MOIS — PRIORITÉ ABSOLUE
    # ======================================================
    if any(
        k in msg
        for k in [
            "ce mois",
            "ce mois-ci",
            "mois en cours",
        ]
    ):
        return {
            "type": "REQUEST_MONTH_RELATIVE",
            "offset": 0,
            "metric": decision.get("metric") or "DISTANCE",
        }

    if any(
        k in msg
        for k in [
            "mois dernier",
            "le mois dernier",
            "mois precedent",
            "mois précédente",
        ]
    ):
        return {
            "type": "REQUEST_MONTH_RELATIVE",
            "offset": -1,
            "metric": decision.get("metric") or "DISTANCE",
        }

    # Mois explicite (septembre, mars, etc.)
    for month_name, month_num in MONTHS.items():
        if re.search(rf"\b{month_name}\b", msg):
            return {
                "type": "REQUEST_MONTH",
                "month": month_num,
                "year": extract_year(msg),
                "metric": decision.get("metric") or "DISTANCE",
            }
    # il y a X mois
    match = re.search(r"(\d+) mois", msg)
    if match:
        return {
            "type": "REQUEST_MONTH_RELATIVE",
            "offset": -int(match.group(1)),
            "metric": decision.get("metric") or "DISTANCE",
        }

    # ======================================================
    # 🔴 ANNÉE RELATIVE — PRIORITÉ ABSOLUE (même hors bilan)
    # ======================================================
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
            "metric": decision.get("metric") or "DISTANCE",
        }

    if any(
        k in msg
        for k in [
            "annee derniere",
            "année dernière",
            "an dernier",
            "annee precedente",
            "année précédente",
        ]
    ):
        return {
            "type": "REQUEST_YEAR_RELATIVE",
            "offset": -1,
            "metric": decision.get("metric") or "DISTANCE",
        }
    year = extract_year(msg)

    if year is not None:
        return {
            "type": "REQUEST_YEAR",
            "year": year,
            "metric": decision.get("metric") or "DISTANCE",
        }

    # il y a X années
    match = re.search(r"(\d+) ans", msg) or re.search(r"(\d+) annees", msg)
    if match:
        return {
            "type": "REQUEST_YEAR_RELATIVE",
            "offset": -int(match.group(1)),
            "metric": decision.get("metric") or "DISTANCE",
        }

    # ======================================================
    # 4️⃣ BILAN SANS PÉRIODE → PÉRIODE COURANTE
    # ======================================================

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

    if is_summary:
        return {"type": "SUMMARY"}

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
    """
    Orchestrateur central.
    Règle absolue :
    - ANSWER_NOW = réponse immédiate, aucune redécision
    - REQUEST_* = soit réponse directe si snapshot match, soit REQUEST_SNAPSHOT
    """
    meta = req.meta or {}
    session_id = meta.get("session_id", "default")

    # ======================================================
    # 🛑 ANSWER_NOW = RÉPONSE IMMÉDIATE, AUCUNE REDÉCISION
    # ======================================================
    if decision.get("type") == "ANSWER_NOW":
        answer_mode = decision.get("answer_mode")
        metric = decision.get("metric", "DISTANCE")

        print("🟢 ANSWER_NOW")
        print("   mode:", answer_mode)
        print("   metric:", metric)

        if answer_mode == "FACTUAL":
            return {
                "type": "ANSWER_NOW",
                "reply": factual_response(req.snapshot, metric)["reply"],
            }

        if answer_mode == "SMALL_TALK":
            session_id = (req.meta or {}).get("session_id", "default")
            return {
                "type": "ANSWER_NOW",
                "reply": answer_with_snapshot(req.message, req.snapshot, session_id),
            }

        # fallback sécurisé
        return {
            "type": "ANSWER_NOW",
            "reply": answer_with_snapshot(req.message, req.snapshot, session_id),
        }

    # ======================================================
    # CONTEXTE GÉNÉRAL
    # ======================================================
    decision_type = decision.get("type")
    metric = decision.get("metric") or "DISTANCE"

    msg = normalize(req.message)
    wants_summary = any(
        k in msg for k in ["bilan", "resume", "résumé", "recap", "synthese", "stat"]
    )

    print("🧠 ROUTE DECISION")
    print("   type:", decision_type)
    print("   metric:", metric)
    print("   wants_summary:", wants_summary)

    # ======================================================
    # 🔒 ANNÉE — SNAPSHOT STRICT
    # ======================================================
    if decision_type in ["REQUEST_YEAR", "REQUEST_YEAR_RELATIVE"]:
        start, end = resolve_period_from_decision(decision, req.message)

        print("🟦 REQUEST_YEAR")
        print("   requested:", start, "→", end)
        print("   snapshot :", req.snapshot.period.start, "→", req.snapshot.period.end)

        if snapshot_matches_period(req.snapshot, start, end):
            print("✅ SNAPSHOT MATCH (YEAR)")
            return {
                "type": "ANSWER_NOW",
                "reply": summary_response(req.snapshot)["reply"],
            }

        print("📤 REQUEST SNAPSHOT (YEAR)")
        return {
            "type": "REQUEST_SNAPSHOT",
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "meta": {
                "metric": metric,
                "reply_mode": "SUMMARY",
            },
        }

    # ======================================================
    # 🔒 SUMMARY PUR (période courante uniquement)
    # ======================================================
    if decision_type == "SUMMARY":
        print("🟢 SUMMARY CURRENT PERIOD")
        return {
            "type": "ANSWER_NOW",
            "reply": summary_response(req.snapshot)["reply"],
        }

    # ======================================================
    # 🔒 SEMAINE — SNAPSHOT STRICT (OFFSET AWARE)
    # ======================================================
    if decision_type == "REQUEST_WEEK":
        offset = decision.get("offset", 0)
        start, end = resolve_period_from_decision(decision, req.message)

        print("🟦 REQUEST_WEEK")
        print("   offset:", offset)
        print("   requested:", start, "→", end)
        print("   snapshot :", req.snapshot.period.start, "→", req.snapshot.period.end)

        if snapshot_matches_period(req.snapshot, start, end):
            print("✅ SNAPSHOT MATCH (WEEK)")
            return {
                "type": "ANSWER_NOW",
                "reply": factual_response(req.snapshot, metric)["reply"],
            }

        print("📤 REQUEST SNAPSHOT (WEEK)")
        return {
            "type": "REQUEST_SNAPSHOT",
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "meta": {
                "metric": metric,
                "reply_mode": "FACTUAL",
                "requested_start": start.isoformat(),
                "requested_end": end.isoformat(),
                "requested_offset": str(offset),
            },
        }

    # ======================================================
    # 🔒 MOIS — SNAPSHOT STRICT
    # ======================================================
    if decision_type in ["REQUEST_MONTH", "REQUEST_MONTH_RELATIVE"]:
        start, end = resolve_period_from_decision(decision, req.message)

        print("🟦 REQUEST_MONTH")
        print("   requested:", start, "→", end)
        print("   snapshot :", req.snapshot.period.start, "→", req.snapshot.period.end)

        if snapshot_matches_period(req.snapshot, start, end):
            print("✅ SNAPSHOT MATCH (MONTH)")
            if wants_summary:
                return {
                    "type": "ANSWER_NOW",
                    "reply": summary_response(req.snapshot)["reply"],
                }
            return {
                "type": "ANSWER_NOW",
                "reply": factual_response(req.snapshot, metric)["reply"],
            }

        print("📤 REQUEST SNAPSHOT (MONTH)")
        return {
            "type": "REQUEST_SNAPSHOT",
            "period": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "meta": {
                "metric": metric,
                "reply_mode": "SUMMARY" if wants_summary else "FACTUAL",
            },
        }

    # ======================================================
    # 🟣 COMPARAISONS
    # ======================================================
    if decision_type == "COMPARE_PERIODS":
        print("🟣 COMPARE_PERIODS")
        return build_compare_request(decision, metric)

    # ======================================================
    # 🟢 FACTUAL DIRECT (sécurité)
    # ======================================================
    if decision.get("answer_mode") == "FACTUAL":
        print("🟢 FACTUAL FALLBACK")
        return {
            "type": "ANSWER_NOW",
            "reply": factual_response(req.snapshot, metric)["reply"],
        }

    # ======================================================
    # 💬 COACHING / SMALL TALK (fallback final)
    # ======================================================
    print("💬 SMALL TALK FALLBACK")
    return {
        "type": "ANSWER_NOW",
        "reply": answer_with_snapshot(req.message, req.snapshot, session_id),
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
