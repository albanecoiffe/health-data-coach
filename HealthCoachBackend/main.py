from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas import ChatRequest

from agents.comparison_agent import comparison_response_agent
from agents.summary_agent import summary_response
from agents.factual_agent import factual_response
from agents.questions_agent import analyze_question

from services.intent import (
    apply_backend_overrides,
    route_decision,
    compute_intensity_split,
)
from services.periods import snapshot_matches_iso
import pandas as pd
from services.memory import store_signature


app = FastAPI()


@app.post("/upload-weeks-csv")
async def upload_csv(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)

    print("📊 CSV reçu")
    print(df.head())

    # sauvegarde
    df.to_csv("weeks_received.csv", index=False)

    return {"status": "ok", "rows": len(df)}


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
    # ======================================================
    # 🧠 SIGNATURE INGESTION
    # ======================================================
    if req.signature and session_id:
        store_signature(session_id, req.signature.model_dump())

    signature = req.signature
    session_id = req.meta.get("session_id")
    if signature:
        print("🧠 SIGNATURE RECEIVED")
        store_signature(session_id, signature)

    # ======================================================
    # 🔒 SNAPSHOT EXACT DÉJÀ FOURNI → RÉPONSE DIRECTE
    # ======================================================
    if req.meta:
        req_start = req.meta.get("requested_start")
        req_end = req.meta.get("requested_end")
        reply_mode = req.meta.get("reply_mode", "FACTUAL")
        metric = req.meta.get("metric", "DISTANCE")

        if req_start and req_end:
            if snapshot_matches_iso(req.snapshot, req_start, req_end):
                print("🟢 SNAPSHOT EXACT — RÉPONSE DIRECTE (NO LLM)")

                if reply_mode == "SUMMARY":
                    reply = summary_response(req.snapshot)["reply"]
                else:
                    reply = factual_response(req.snapshot, metric)["reply"]

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
    # 🔵 FLOW NORMAL — ANALYSE + VERROUS BACKEND
    # ======================================================
    decision = analyze_question(
        req.message,
        (req.snapshot.period.start, req.snapshot.period.end),
    )

    decision = apply_backend_overrides(req.message, decision)

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
