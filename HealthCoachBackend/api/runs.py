# import
from fastapi import APIRouter, Query
from datetime import date
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from core.models.RunSession import RunSession
from schemas.schemas import RunSessionCreate
from core.services.signature.signature_store import invalidate_signature
from core.services.run_weeks.builder import build_run_weeks
from core.services.run_sessions.loader import load_run_sessions

router = APIRouter(prefix="/api")


def _create_run_session_from_payload(payload: RunSessionCreate) -> RunSession:
    return RunSession(
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


def _apply_payload_to_session(session: RunSession, payload: RunSessionCreate) -> None:
    session.distance_km = payload.distance_km
    session.duration_min = payload.duration_min
    session.avg_hr = payload.avg_hr
    session.z1_min = payload.z1_min
    session.z2_min = payload.z2_min
    session.z3_min = payload.z3_min
    session.z4_min = payload.z4_min
    session.z5_min = payload.z5_min
    session.elevation_m = payload.elevation_m
    session.active_kcal = payload.active_kcal


def _upsert_run_session(db, payload: RunSessionCreate) -> str:
    existing = (
        db.query(RunSession)
        .filter(
            RunSession.user_id == payload.user_id,
            RunSession.start_time == payload.start_time,
        )
        .first()
    )

    if existing:
        _apply_payload_to_session(existing, payload)
        db.commit()
        return "updated"

    db.add(_create_run_session_from_payload(payload))
    db.commit()
    return "inserted"


# ======================================================
# 🏃 ENDPOINTS SÉANCES DE COURSE
# ======================================================
@router.post("/run-session")
def ingest_run_session(payload: RunSessionCreate):
    print("📥 INGEST:", payload.start_time)
    db = SessionLocal()

    try:
        status = _upsert_run_session(db, payload)

        # 🔁 1️⃣ Rebuild / upsert RunWeek
        print("🔄 Rebuilding RunWeek for user", payload.user_id)
        build_run_weeks(db, payload.user_id)

        # 🔁 2️⃣ Invalider la signature
        print("♻️ Invalidating signature for user", payload.user_id)
        invalidate_signature(db, payload.user_id)

        return {"status": status}

    except IntegrityError:
        db.rollback()
        return {"status": "duplicate"}

    finally:
        db.close()


@router.post("/run-sessions/batch")
def ingest_run_sessions_batch(payloads: list[RunSessionCreate]):
    if not payloads:
        return {"status": "ok", "inserted": 0, "updated": 0, "duplicates": 0}

    db = SessionLocal()
    inserted = 0
    updated = 0
    duplicates = 0
    touched_users = set()

    try:
        for payload in payloads:
            touched_users.add(payload.user_id)
            try:
                status = _upsert_run_session(db, payload)
                if status == "inserted":
                    inserted += 1
                elif status == "updated":
                    updated += 1
            except IntegrityError:
                db.rollback()
                duplicates += 1

        for user_id in touched_users:
            build_run_weeks(db, user_id)
            invalidate_signature(db, user_id)

        return {
            "status": "ok",
            "inserted": inserted,
            "updated": updated,
            "duplicates": duplicates,
            "total": len(payloads),
        }
    finally:
        db.close()


@router.get("/run-sessions")
def get_run_sessions(
    user_id: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    db = SessionLocal()
    try:
        sessions = load_run_sessions(db, user_id)

        filtered = [
            s for s in sessions if start_date <= s["start_time"].date() < end_date
        ]

        return filtered

    finally:
        db.close()
