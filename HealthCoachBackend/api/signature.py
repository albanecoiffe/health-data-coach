from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from database import SessionLocal
from services.signature_builder import build_runner_signature
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
    return build_runner_signature(db=db, user_id=user_id)
