from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas import ChatRequest

from agents.comparison_agent import comparison_response_agent
from agents.small_talks_agent import answer_small_talk
from agents.summary_agent import summary_response
from agents.factual_agent import factual_response
from agents.questions_agent import analyze_question
from services.intent_gatekeeper import intent_gatekeeper

from services.intent import (
    apply_backend_overrides,
    route_decision,
    compute_intensity_split,
)
from services.periods import snapshot_matches_iso
import pandas as pd
from services.memory import (
    store_signature,
    set_last_metric,
    get_last_metric,
    add_to_memory,
)

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from services.database import engine

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from services.database import SessionLocal
from models import RunSession
from schemas import RunSessionCreate


app = FastAPI()

# =====================================================
# 🏥 ENDPOINTS data
# =====================================================

router = APIRouter()


@app.get("/health/db")
def db_health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"db": "ok"}


# =====================================================
# 🛠️ ENDPOINTS DE DEBUG
# =====================================================
from sqlalchemy import inspect
from services.database import engine


@app.get("/debug/tables")
def list_tables():
    inspector = inspect(engine)
    return inspector.get_table_names()


# ======================================================
# 🏃 ENDPOINTS SÉANCES DE COURSE
# ======================================================
@app.post("/api/run-session")
def ingest_run_session(
    payload: RunSessionCreate,
):
    db = SessionLocal()

    try:
        session = RunSession(
            user_id=payload.user_id,
            start_time=payload.start_time,
            distance_km=payload.distance_km,
            duration_min=payload.duration_min,
            avg_hr=payload.avg_hr,
            z1_min=payload.z1_min,
            z2_min=payload.z2_min,
            z3_min=payload.z3_min,
            z4_min=payload.z4_min,
            z5_min=payload.z5_min,
            elevation_m=payload.elevation_m,
            active_kcal=payload.active_kcal,
        )

        db.add(session)
        db.commit()

        return {"status": "inserted"}

    except IntegrityError:
        db.rollback()
        # Doublon (user_id + start_time)
        return {"status": "duplicate"}

    finally:
        db.close()


# ======================================================
# 📊 ENDPOINTS D'IMPORTATION DE CSV
# ======================================================
@app.post("/upload-weeks-csv")
async def upload_csv(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)

    print("📊 CSV reçu")
    print(df.head())

    # sauvegarde
    df.to_csv("weeks_received.csv", index=False)

    return {"status": "ok", "rows": len(df)}


@app.post("/upload-sessions-csv")
async def upload_sessions_csv(file: UploadFile = File(...)):
    dt = pd.read_csv(file.file)

    print("📊 CSV reçu")
    print(dt.head())
    dt.to_csv("sessions_received.csv", index=False)
    return {"status": "ok", "rows": len(dt)}


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
    print("\n================= CHAT =================")
    print("📝 MESSAGE :", req.message)
    print("📦 SNAPSHOT REÇU")
    print("   Période :", req.snapshot.period.start, "→", req.snapshot.period.end)
    print("🔥 snapshots =", req.snapshots)
    print("🔥 meta =", req.meta)

    session_id = (req.meta or {}).get("session_id")
    # 🔴 MÉMOIRE — message utilisateur (CRITIQUE)
    if session_id:
        add_to_memory(session_id, "user", req.message)

    # ======================================================
    # 🧠 SIGNATURE INGESTION
    # ======================================================
    if req.signature and session_id:
        print("🧠 SIGNATURE RECEIVED")
        store_signature(session_id, req.signature.model_dump())

    # ======================================================
    # 🔒 SNAPSHOT EXACT DÉJÀ FOURNI → RÉPONSE DIRECTE
    # ======================================================
    if req.meta:
        req_start = req.meta.get("requested_start")
        req_end = req.meta.get("requested_end")
        reply_mode = req.meta.get("reply_mode", "FACTUAL")
        metric = req.meta.get("metric", "DISTANCE")

        if snapshot_matches_iso(req.snapshot, req_start, req_end):
            print("🟢 SNAPSHOT EXACT — RÉPONSE DIRECTE (NO LLM)")

            if reply_mode == "SUMMARY":
                reply = summary_response(req.snapshot)["reply"]
            else:
                reply = factual_response(req.snapshot, metric)["reply"]

            # 🧠 MÉMOIRE — réponse assistant (CRITIQUE)
            add_to_memory(session_id, "assistant", reply)

            # 🧠 STOCKAGE DE LA MÉTRIQUE
            set_last_metric(session_id, metric)

            return {
                "type": "ANSWER_NOW",
                "reply": reply,
            }

    # ======================================================
    # 🔴 COMPARAISON FINALE — PRIORITÉ ABSOLUE
    # ======================================================
    if req.snapshots is not None and req.meta is not None:
        print("🟢 COMPARAISON FINALE — SNAPSHOTS PRÉSENTS")

        left = req.snapshots.left
        right = req.snapshots.right

        # 🔢 CALCULS STRICTEMENT BACKEND
        raw_delta_distance = left.totals.distance_km - right.totals.distance_km
        raw_delta_duration = left.totals.duration_min - right.totals.duration_min
        raw_delta_sessions = left.totals.sessions - right.totals.sessions

        trend = (
            "UP"
            if raw_delta_distance > 0
            else "DOWN"
            if raw_delta_distance < 0
            else "STABLE"
        )

        delta = {
            "distance_km": round(raw_delta_distance, 1),
            "duration_min": round(raw_delta_duration),
            "sessions": raw_delta_sessions,
            "trend": trend,
        }
        # ❤️ INTENSITÉ — CALCUL BACKEND
        left_intensity = compute_intensity_split(left)
        right_intensity = compute_intensity_split(right)

        if left_intensity and right_intensity:
            intensity_delta = {
                "low_pct": round(
                    left_intensity["low_pct"] - right_intensity["low_pct"], 1
                ),
                "high_pct": round(
                    left_intensity["high_pct"] - right_intensity["high_pct"], 1
                ),
            }
        else:
            intensity_delta = None

        print("📊 DELTA CALCULÉ :", delta)

        # 🧱 BLOC MÉTRIQUES DÉTERMINISTE (JAMAIS LLM)
        metrics_block = (
            f"🏃 Distance : {delta['distance_km']} km\n"
            f"⏱️ Durée : {delta['duration_min']} minutes\n"
            f"📆 Séances : {delta['sessions']}\n"
        )
        if intensity_delta:
            intensity_block = (
                "❤️ Intensité\n"
                f"- 🟢 Z1–Z3 : {intensity_delta['low_pct']} %\n"
                f"- 🔴 Z4–Z5 : {intensity_delta['high_pct']} %\n"
            )
        else:
            intensity_block = ""
        print(
            f"🧪 CHECK COMPARISON | LEFT={left.totals.distance_km} km | "
            f"RIGHT={right.totals.distance_km} km | RAW_DELTA={raw_delta_distance}"
        )

        # 🧠 TEXTE HUMAIN (LLM, SANS CHIFFRES)
        narrative_text = comparison_response_agent(
            message=req.message,
            metric=req.meta.get("metric", "DISTANCE"),
            delta=delta,
            left_period=(left.period.start, left.period.end),
            right_period=(right.period.start, right.period.end),
            period_context=req.meta.get("period_context"),
        )

        # 🧩 ASSEMBLAGE FINAL
        final_reply = f"{narrative_text}\n\n{metrics_block}" + (
            f"\n\n{intensity_block}" if intensity_block else ""
        )

        return {
            "type": "ANSWER_NOW",
            "reply": final_reply,
        }

    # ======================================================
    # 🧠 INTENT GATEKEEPER — FILTRE HAUT NIVEAU
    # ======================================================
    intent = intent_gatekeeper(req.message)

    if intent["intent_type"] == "RECOMMENDATION":
        decision = {"type": "RECOMMENDATION"}

    elif intent["intent_type"] in {"QUESTION", "ACTION"}:
        decision = analyze_question(
            req.message,
            (req.snapshot.period.start, req.snapshot.period.end),
        )
        decision = apply_backend_overrides(req.message, decision)

        # ======================================================
        # 🔁 HÉRITAGE DE MÉTRIQUE (CONTEXTE IMPLICITE)
        # ======================================================
        last_metric = get_last_metric(session_id)

        if last_metric:
            # Cas 1 — aucune métrique détectée
            if "metric" not in decision or decision.get("metric") in {None, "UNKNOWN"}:
                decision["metric"] = last_metric
                print("🧠 METRIC INHERITED (missing):", last_metric)

            # Cas 2 — métrique par défaut injectée par le LLM
            elif decision.get("metric") == "DISTANCE":
                # heuristique linguistique simple
                if req.message.lower().startswith(
                    ("et ", "et de", "et celle", "et celui")
                ):
                    decision["metric"] = last_metric
                    print("🧠 METRIC OVERRIDDEN (elliptical):", last_metric)

    else:
        # déclaration / small talk
        return {
            "type": "ANSWER_NOW",
            "reply": answer_small_talk(req.message, session_id),
        }

    print("\n================= DECISION =================")
    print("🧠 DECISION :", decision)

    # ======================================================
    # 🧭 ROUTING CENTRALISÉ
    # ======================================================
    result = route_decision(req, decision)

    # ======================================================
    # 🔒 PASS-THROUGH DES REQUEST_* (CRITIQUE)
    # ======================================================
    if isinstance(result, dict) and result.get("type", "").startswith("REQUEST_"):
        return result

    # ======================================================
    # 🟢 RÉPONSE FINALE NORMALISÉE
    # ======================================================
    if isinstance(result, dict) and "reply" in result:
        metric = decision.get("metric")
        if metric:
            set_last_metric(session_id, metric)

        if session_id:
            add_to_memory(session_id, "assistant", result["reply"])

        return {
            "type": result.get("type", "ANSWER_NOW"),
            "reply": result["reply"],
        }

    # ======================================================
    # ❌ FALLBACK ABSOLU
    # ======================================================
    return {
        "type": "ANSWER_NOW",
        "reply": "Une erreur inattendue est survenue.",
    }
