# import
from fastapi import APIRouter
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database import SessionLocal
from models.models import RunSession
from schemas.schemas import RunSessionCreate

router = APIRouter(prefix="/api")


# ======================================================
# 🏃 ENDPOINTS SÉANCES DE COURSE
# ======================================================
@router.post("/run-session")
def ingest_run_session(payload: RunSessionCreate):
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
