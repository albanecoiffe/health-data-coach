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
from services.periods import get_current_week_interval

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

from datetime import datetime, timedelta


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
    print("🧪 META :", req.meta)

    # ======================================================
    # 🧍 USER IDENTIFICATION
    # ======================================================
    if req.meta and "user_id" in req.meta:
        user_uuid = UUID(req.meta["user_id"])
    elif DEFAULT_USER_ID:
        user_uuid = DEFAULT_USER_ID
    else:
        raise HTTPException(status_code=400, detail="Missing user_id")

    session_id = req.meta.get("session_id") if req.meta else None

    if session_id:
        add_to_memory(session_id, "user", req.message)

    # ======================================================
    # 🗄️ DB
    # ======================================================
    db = SessionLocal()
    try:
        # 🔹 Snapshot par défaut = semaine courante
        start, end = get_current_week_interval()

        snapshot = get_snapshot_from_store(
            db=db,
            user_id=user_uuid,
            start=start,
            end=end,
        )

        if snapshot is None:
            return {
                "type": "ANSWER_NOW",
                "reply": "Je n’ai pas encore assez de données pour t’analyser.",
            }

        signature = get_signature_from_store(db, user_uuid)

    finally:
        db.close()

    # ======================================================
    # 🧠 INTENT
    # ======================================================
    intent = intent_gatekeeper(req.message)

    if intent["intent_type"] == "SMALL_TALK":
        return {
            "type": "ANSWER_NOW",
            "reply": answer_small_talk(req.message, session_id),
        }

    # ======================================================
    # 🧠 QUESTIONS / ACTIONS
    # ======================================================
    if intent["intent_type"] in {"QUESTION", "ACTION"}:
        decision = analyze_question(
            req.message,
            (snapshot.period.start, snapshot.period.end),
        )
        decision = apply_backend_overrides(req.message, decision)

        last_metric = get_last_metric(session_id)
        if last_metric and decision.get("metric") in {None, "UNKNOWN", "DISTANCE"}:
            decision["metric"] = last_metric

    elif intent["intent_type"] == "RECOMMENDATION":
        decision = {"type": "RECOMMENDATION"}

    else:
        return {
            "type": "ANSWER_NOW",
            "reply": answer_small_talk(req.message, session_id),
        }

    print("🧠 DECISION :", decision)

    # ======================================================
    # 🧭 ROUTING
    # ======================================================
    result = route_decision(
        decision=decision,
        db=db,
        user_id=user_uuid,
        message=req.message,
        session_id=session_id,
    )

    # ======================================================
    # 🟢 FINAL
    # ======================================================
    if isinstance(result, dict) and "reply" in result:
        if session_id:
            add_to_memory(session_id, "assistant", result["reply"])
        if decision.get("metric"):
            set_last_metric(session_id, decision["metric"])

        return {
            "type": result.get("type", "ANSWER_NOW"),
            "reply": result["reply"],
        }

    return {
        "type": "ANSWER_NOW",
        "reply": "Une erreur inattendue est survenue.",
    }
