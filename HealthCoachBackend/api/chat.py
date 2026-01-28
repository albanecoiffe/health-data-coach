from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas.schemas import ChatRequest

from agents.comparison_agent import comparison_response_agent
from agents.small_talks_agent import answer_small_talk
from agents.summary_agent import summary_response
from agents.factual_agent import factual_response
from agents.questions_agent import analyze_question
from services.intent_gatekeeper import intent_gatekeeper

from services.snapshot.store import get_snapshot_from_store
from services.signature.store import get_signature_from_store

from datetime import datetime
from database import SessionLocal

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

import os
from uuid import UUID

DEFAULT_USER_ID = (
    UUID(os.getenv("DEFAULT_USER_ID")) if os.getenv("DEFAULT_USER_ID") else None
)


router = APIRouter()


# ======================================================
# 💬 ENDPOINT CHAT
# ======================================================
@router.post("/chat")
def chat(req: ChatRequest):
    print("\n================= CHAT =================")
    print("📝 MESSAGE :", req.message)
    print("📦 SNAPSHOT REÇU (transport)")

    if req.snapshot:
        print("   →", req.snapshot.period.start, "→", req.snapshot.period.end)

    print("🔥 snapshots =", req.snapshots)
    print("🔥 meta =", req.meta)
    print("🧪 META REÇU :", req.meta)

    session_id = req.meta.session_id if req.meta else None

    # ======================================================
    # 🧍 USER IDENTIFICATION (SOURCE OF TRUTH)
    # ======================================================
    if req.meta and req.meta.user_id:
        user_uuid = UUID(req.meta.user_id)
    elif DEFAULT_USER_ID:
        user_uuid = DEFAULT_USER_ID
    else:
        raise HTTPException(status_code=400, detail="Missing user_id")

    # 🔴 MÉMOIRE — message utilisateur (CRITIQUE)
    if session_id:
        add_to_memory(session_id, "user", req.message)

    # ======================================================
    # 🗄️ OUVERTURE DB (UNE SEULE FOIS)
    # ======================================================
    db = SessionLocal()
    try:
        # ======================================================
        # 🔁 SNAPSHOT BACKEND
        # ======================================================
        if req.meta and req.meta.requested_start and req.meta.requested_end:
            snapshot = get_snapshot_from_store(
                db,
                user_uuid,
                req.meta.requested_start,
                req.meta.requested_end,
            )

            if snapshot:
                req.snapshot = snapshot

                print("📦 SNAPSHOT BACKEND UTILISÉ")
                print(
                    "   →",
                    req.snapshot.period.start,
                    "→",
                    req.snapshot.period.end,
                )

        # ======================================================
        # 🧠 SIGNATURE BACKEND
        # ======================================================
        if session_id:
            signature = get_signature_from_store(db, user_uuid)
            if signature:
                req.signature = signature

    finally:
        db.close()

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
        req_start = req.meta.requested_start
        req_end = req.meta.requested_end
        reply_mode = req.meta.reply_mode or "FACTUAL"
        metric = req.meta.metric or "DISTANCE"

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
            metric=req.meta.metric,
            delta=delta,
            left_period=(left.period.start, left.period.end),
            right_period=(right.period.start, right.period.end),
            period_context=req.meta.period_context,
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
