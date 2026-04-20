from uuid import UUID

from fastapi import APIRouter, HTTPException

from core.config import get_settings
from database import SessionLocal
from intents.intent_detector import detect_intent
from routing.router import route_intent
from schemas.schemas import ChatRequest

DEFAULT_USER_ID = get_settings().default_user_uuid

router = APIRouter()


def _resolve_user_id(meta: dict | None) -> UUID:
    if meta and "user_id" in meta:
        return UUID(meta["user_id"])
    if DEFAULT_USER_ID:
        return DEFAULT_USER_ID
    raise HTTPException(status_code=400, detail="Missing user_id")


@router.post("/chat")
def chat(req: ChatRequest):
    print("\n================= CHAT V2 =================")
    print("📝 USER MESSAGE :", req.message)
    print("🧪 META :", req.meta)

    user_id = _resolve_user_id(req.meta)

    db = SessionLocal()
    try:
        intent = detect_intent(req.message)
        print("🧠 RAW INTENT (LLM) :", intent)

        result = route_intent(db, user_id, intent)
        print("📦 FINAL RESULT :", result)
        print("================= END CHAT =================\n")

    finally:
        db.close()

    return result
