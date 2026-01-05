from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas import ChatRequest
from agent import (
    analyze_question,
    answer_with_snapshot,
    factual_response,
    comparison_response_agent,
    summary_response,
)
import re
from services.periods import period_to_dates, normalize, resolve_period
from services.comparisons import compare_snapshots, resolve_intent
from services.router import snapshot_matches

from datetime import date, timedelta
import calendar

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

app = FastAPI()


# ======================================================
# ❌ HANDLER ERREUR VALIDATION
# ======================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print("❌ ERREUR DE VALIDATION FASTAPI")
    print("BODY :", await request.body())
    print("DETAILS :", exc.errors())
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/")
def root():
    return {"status": "ok"}


# ======================================================
# 💬 ENDPOINT CHAT
# ======================================================
@app.post("/chat")
def chat(req: ChatRequest):
    intent = resolve_intent(req.message)
    print("\n================= CHAT =================")
    print("📝 MESSAGE :", req.message)
    print("📦 SNAPSHOT REÇU PAR LE BACKEND")
    print("   Période :", req.snapshot.period.start, "→", req.snapshot.period.end)

    print("   📏 Distance (km) :", req.snapshot.totals.distance_km)
    print("   ⏱️ Durée (min)   :", req.snapshot.totals.duration_min)
    print("   📆 Séances       :", req.snapshot.totals.sessions)

    # ======================================================
    # 🔴 COMPARAISON FINALE — PRIORITÉ ABSOLUE
    # ⚠️ snapshots + meta présents → AUCUN LLM DE DÉCISION
    # ======================================================
    if req.snapshots is not None and req.meta is not None:
        print("🟢 COMPARAISON FINALE — SNAPSHOTS PRÉSENTS")

        left = req.snapshots.left
        right = req.snapshots.right

        delta = {
            "distance_km": round(left.totals.distance_km - right.totals.distance_km, 1),
            "duration_min": round(left.totals.duration_min - right.totals.duration_min),
            "sessions": left.totals.sessions - right.totals.sessions,
        }

        reply = comparison_response_agent(
            message=req.message,
            metric=req.meta.get("metric", "DISTANCE"),
            delta=delta,
            left_label=req.meta.get("left_label", "période 1"),
            right_label=req.meta.get("right_label", "période 2"),
        )

        return {"reply": reply}

    # ======================================================
    # 🔵 FLOW NORMAL — ANALYSE LLM AUTORISÉE
    # ======================================================
    print(
        "📦 SNAPSHOT :",
        req.snapshot.period.start,
        "→",
        req.snapshot.period.end,
    )

    decision = analyze_question(
        req.message,
        (req.snapshot.period.start, req.snapshot.period.end),
    )

    msg = normalize(req.message)

    # 🛡️ VERROU BACKEND — DEMANDE DE BILAN
    if any(
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
    ):
        decision = {"type": "SUMMARY"}
        print("🛡️ OVERRIDE BACKEND → SUMMARY")

    # 🛡️ VERROU BACKEND — COMPARAISON EXPLICITE (priorité absolue)
    if any(
        k in msg
        for k in [
            "difference entre",
            "différence entre",
            "comparaison",
            "compare",
            "comparé",
            "comparaison entre",
            "évolution entre",
            "évolution par rapport à",
        ]
    ):
        if "semaine" in msg and "precedent" in msg:
            decision = {
                "type": "COMPARE_PERIODS",
                "metric": decision.get("metric") or "DISTANCE",
                "left": "CURRENT_WEEK",
                "right": "PREVIOUS_WEEK",
            }
            print("🛡️ OVERRIDE BACKEND → COMPARAISON SEMAINE")

    # 🛡️ VERROU BACKEND — MOIS NOMMÉ (octobre, mars, etc.)
    msg = normalize(req.message)

    # 🛡️ VERROU BACKEND — MOIS NOMMÉ (mot entier uniquement)
    for month_name, month_num in MONTHS.items():
        pattern = rf"\b{month_name}\b"
        if re.search(pattern, msg):
            decision = {
                "type": "REQUEST_MONTH",
                "month": month_num,
                "year": None,
                "metric": decision.get("metric") or "DISTANCE",
            }
            print(f"🛡️ OVERRIDE BACKEND → mois détecté : {month_name}")
            break

    # 🛡️ VERROU BACKEND — semaine précédente = REQUEST_WEEK
    if decision.get("type") != "COMPARE_PERIODS":
        if any(
            k in msg
            for k in [
                "semaine precedente",
                "semaine derniere",
                "la semaine d'avant",
                "semaine d’avant",
                "precedente",
            ]
        ):
            decision = {
                "type": "REQUEST_WEEK",
                "offset": -1,
                "metric": decision.get("metric") or "DISTANCE",
            }
            print("🛡️ OVERRIDE BACKEND → semaine précédente = REQUEST_WEEK (-1)")

    # 🛡️ VERROU BACKEND — cette semaine = FACTUAL
    if decision.get("type") == "ANSWER_NOW" and (
        "cette semaine" in req.message.lower()
        or "semaine en cours" in req.message.lower()
        or "semaine actuelle" in req.message.lower()
    ):
        decision = {
            "type": "ANSWER_NOW",
            "answer_mode": "FACTUAL",
            "metric": decision.get("metric") or "DISTANCE",
        }
        print("🛡️ OVERRIDE BACKEND → cette semaine = ANSWER_NOW (FACTUAL)")

    decision_type = decision.get("type", "ANSWER_NOW")
    answer_mode = decision.get("answer_mode")
    metric = decision.get("metric") or "DISTANCE"
    offset = decision.get("offset")

    print("\n================= ROUTING =================")
    print("🧠 DECISION TYPE :", decision_type)
    print("🧠 ANSWER MODE   :", answer_mode)
    print("🧠 METRIC        :", metric)
    print("🧠 OFFSET        :", offset)

    # ======================================================
    # 🟠 REQUEST_WEEK
    # ======================================================
    if decision_type == "REQUEST_WEEK":
        offset = int(offset if offset is not None else -1)

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        start = week_start + timedelta(days=7 * offset)
        end = start + timedelta(days=7)

        print("📆 TARGET_WEEK :", start, "→", end)

        if (
            req.snapshot.period.start == start.isoformat()
            and req.snapshot.period.end == end.isoformat()
        ):
            print("✅ SEMAINE DÉJÀ CHARGÉE → FACTUAL")
            return factual_response(req.snapshot, metric)

        return {
            "type": "REQUEST_SNAPSHOT",
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "meta": {"metric": metric},
        }

    # ======================================================
    # 🟠 REQUEST_MONTH (ABSOLU)
    # ======================================================
    if decision_type == "REQUEST_MONTH":
        month = decision.get("month")
        raw_year = decision.get("year")

        if month is None:
            return {
                "reply": (
                    "Je n’ai pas compris quel mois précis tu voulais. "
                    "Peux-tu préciser (ex: 'novembre 2025') ?"
                )
            }

        month = int(month)
        today = date.today()

        if isinstance(raw_year, int):
            year = raw_year

            if year > today.year or (year == today.year and month > today.month):
                year = today.year - 1
        else:
            # Mois sans année → dernier mois écoulé
            if month < today.month:
                year = today.year
            else:
                year = today.year - 1

        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])

        if (
            req.snapshot.period.start == start.isoformat()
            and req.snapshot.period.end == end.isoformat()
        ):
            print("✅ MOIS DÉJÀ CHARGÉ → FACTUAL")
            return factual_response(req.snapshot, metric)

        return {
            "type": "REQUEST_SNAPSHOT",
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "meta": {"metric": metric},
        }

    # ======================================================
    # 🟠 REQUEST_MONTH_RELATIVE
    # ======================================================
    if decision_type == "REQUEST_MONTH_RELATIVE":
        msg = normalize(req.message)

        if "ce mois" in msg:
            offset = 0
        elif "mois dernier" in msg:
            offset = -1
        else:
            offset = int(offset or -1)

        today = date.today()
        target_month = today.month + offset
        target_year = today.year

        while target_month < 1:
            target_month += 12
            target_year -= 1
        while target_month > 12:
            target_month -= 12
            target_year += 1

        start = date(target_year, target_month, 1)
        end = date(
            target_year,
            target_month,
            calendar.monthrange(target_year, target_month)[1],
        )

        if (
            req.snapshot.period.start == start.isoformat()
            and req.snapshot.period.end == end.isoformat()
        ):
            print("✅ MOIS RELATIF DÉJÀ CHARGÉ → FACTUAL")
            return factual_response(req.snapshot, metric)

        return {
            "type": "REQUEST_SNAPSHOT",
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "meta": {"metric": metric},
        }

    # ======================================================
    # 🟣 COMPARE_PERIODS → DEMANDE SNAPSHOTS
    # ======================================================
    if decision_type == "COMPARE_PERIODS":
        left_start, left_end = period_to_dates(decision["left"])
        right_start, right_end = period_to_dates(decision["right"])

        LABELS = {
            "CURRENT_WEEK": "cette semaine",
            "PREVIOUS_WEEK": "la semaine dernière",
            "CURRENT_MONTH": "ce mois-ci",
            "PREVIOUS_MONTH": "le mois dernier",
        }

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
                "left_label": LABELS.get(decision["left"], "période 1"),
                "right_label": LABELS.get(decision["right"], "période 2"),
            },
        }
    # ======================================================

    # 🟡 SUMMARY AVEC PÉRIODE RELATIVE
    # ======================================================
    print("DAILY RUNS COUNT:", len(req.snapshot.daily_runs))
    print("RAW SNAPSHOT KEYS:", req.snapshot.model_dump().keys())
    print("DAILY RUNS:", len(req.snapshot.daily_runs))

    if decision_type == "SUMMARY":
        msg = normalize(req.message)

        # Cas : ce mois-ci
        if "ce mois" in msg or "ce mois ci" in msg:
            today = date.today()
            start = date(today.year, today.month, 1)
            end = date(
                today.year,
                today.month,
                calendar.monthrange(today.year, today.month)[1],
            )

            # Snapshot déjà chargé ?
            if (
                req.snapshot.period.start == start.isoformat()
                and req.snapshot.period.end == end.isoformat()
            ):
                return summary_response(req.snapshot)

            return {
                "type": "REQUEST_SNAPSHOT",
                "period": {"start": start.isoformat(), "end": end.isoformat()},
            }

        # Sinon → summary sur la période courante
        return summary_response(req.snapshot)

    # ======================================================
    # 🟢 ANSWER_NOW
    # ======================================================
    if answer_mode == "FACTUAL":
        return factual_response(req.snapshot, metric)

    return {"reply": answer_with_snapshot(req.message, req.snapshot)}
