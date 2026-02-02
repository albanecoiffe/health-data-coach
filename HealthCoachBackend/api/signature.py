from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from database import SessionLocal
from services.signature.builder import build_runner_signature
from services.signature.signature_service import get_signature_from_store
from schemas.signature import RunnerSignature

router = APIRouter(prefix="/api")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/runner-signature", response_model=RunnerSignature)
def get_runner_signature(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    print("🔥 runner-signature endpoint called")
    return get_signature_from_store(db, user_id)
