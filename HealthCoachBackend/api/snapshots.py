from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from database import SessionLocal
from services.snapshot.builder import build_snapshot_from_db
from schemas.schemas import WeeklySnapshot
from uuid import UUID

router = APIRouter(prefix="/api")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/snapshot", response_model=WeeklySnapshot)
def get_snapshot(
    user_id: UUID,
    start: datetime,
    end: datetime,
    db: Session = Depends(get_db),
):
    return build_snapshot_from_db(db, user_id, start, end)
