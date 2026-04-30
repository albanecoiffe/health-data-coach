# import
from fastapi import APIRouter, HTTPException, Query, Request
from datetime import date, datetime, timezone
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from api.auth import assert_import_token
from database import SessionLocal
from core.models.RunSession import RunSession
from schemas.schemas import RunSessionCreate, RunSessionMetadataUpdate
from core.services.signature.signature_store import invalidate_signature
from core.services.run_weeks.builder import build_run_weeks
from core.services.run_sessions.loader import load_run_sessions
from core.services.session_type_predictor import predict_session_type

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
        session_type=payload.session_type,
        session_detail=payload.session_detail,
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
    if payload.session_type is not None:
        session.session_type = payload.session_type
    if payload.session_detail is not None:
        session.session_detail = payload.session_detail


def _same_optional_float(left, right) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return abs(float(left) - float(right)) < 0.000001


def _session_matches_payload(session: RunSession, payload: RunSessionCreate) -> bool:
    return (
        _same_optional_float(session.distance_km, payload.distance_km)
        and _same_optional_float(session.duration_min, payload.duration_min)
        and _same_optional_float(session.avg_hr, payload.avg_hr)
        and _same_optional_float(session.z1_min, payload.z1_min)
        and _same_optional_float(session.z2_min, payload.z2_min)
        and _same_optional_float(session.z3_min, payload.z3_min)
        and _same_optional_float(session.z4_min, payload.z4_min)
        and _same_optional_float(session.z5_min, payload.z5_min)
        and _same_optional_float(session.elevation_m, payload.elevation_m)
        and _same_optional_float(session.active_kcal, payload.active_kcal)
    )


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
        if _session_matches_payload(existing, payload):
            return "duplicate"
        _apply_payload_to_session(existing, payload)
        db.commit()
        return "updated"

    db.add(_create_run_session_from_payload(payload))
    db.commit()
    return "inserted"


def _serialize_session_metadata(db, session: RunSession) -> dict:
    predicted = None
    if not session.session_type:
        predicted = predict_session_type(db, session.user_id, session)

    effective = session.session_type or predicted

    return {
        "start_time": session.start_time.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "session_type": session.session_type,
        "predicted_session_type": predicted,
        "effective_session_type": effective,
        "session_detail": session.session_detail,
    }


# ======================================================
# 🏃 ENDPOINTS SÉANCES DE COURSE
# ======================================================
@router.post("/run-session")
def ingest_run_session(request: Request, payload: RunSessionCreate):
    assert_import_token(request)
    print("📥 INGEST:", payload.start_time)
    db = SessionLocal()

    try:
        status = _upsert_run_session(db, payload)

        # 🔁 1️⃣ Rebuild / upsert RunWeek
        print("🔄 Rebuilding touched RunWeek for user", payload.user_id)
        build_run_weeks(db, payload.user_id, touched_dates=[payload.start_time])

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
def ingest_run_sessions_batch(request: Request, payloads: list[RunSessionCreate]):
    assert_import_token(request)
    if not payloads:
        return {"status": "ok", "inserted": 0, "updated": 0, "duplicates": 0}

    batch_start = min(payload.start_time for payload in payloads)
    batch_end = max(payload.start_time for payload in payloads)
    db = SessionLocal()
    inserted = 0
    updated = 0
    duplicates = 0
    dirty_users = set()
    dirty_week_dates = {}

    try:
        for payload in payloads:
            try:
                status = _upsert_run_session(db, payload)
                if status == "inserted":
                    inserted += 1
                    dirty_users.add(payload.user_id)
                    dirty_week_dates.setdefault(payload.user_id, set()).add(payload.start_time)
                elif status == "updated":
                    updated += 1
                    dirty_users.add(payload.user_id)
                    dirty_week_dates.setdefault(payload.user_id, set()).add(payload.start_time)
                elif status == "duplicate":
                    duplicates += 1
            except IntegrityError:
                db.rollback()
                duplicates += 1

        for user_id in dirty_users:
            build_run_weeks(
                db,
                user_id,
                touched_dates=dirty_week_dates.get(user_id, set()),
            )
            invalidate_signature(db, user_id)

        print(
            "📥 BATCH run-sessions:",
            f"total={len(payloads)}",
            f"inserted={inserted}",
            f"updated={updated}",
            f"duplicates={duplicates}",
            f"from={batch_start}",
            f"to={batch_end}",
            f"rebuild_users={len(dirty_users)}",
        )

        return {
            "status": "ok",
            "inserted": inserted,
            "updated": updated,
            "duplicates": duplicates,
            "total": len(payloads),
        }
    finally:
        db.close()


@router.get("/run-sessions/latest")
def get_latest_run_session(user_id: str):
    db = SessionLocal()
    try:
        latest = (
            db.query(func.max(RunSession.start_time))
            .filter(RunSession.user_id == user_id)
            .scalar()
        )
        total = db.query(RunSession).filter(RunSession.user_id == user_id).count()

        if latest is None:
            latest_iso = None
        else:
            latest_iso = latest.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

        return {
            "user_id": user_id,
            "total": total,
            "latest_start_time": latest_iso,
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


@router.get("/run-sessions/metadata")
def get_run_sessions_metadata(
    user_id: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.min.time())

    db = SessionLocal()
    try:
        sessions = (
            db.query(RunSession)
            .filter(
                RunSession.user_id == user_id,
                RunSession.start_time >= start_dt,
                RunSession.start_time < end_dt,
            )
            .order_by(RunSession.start_time.asc())
            .all()
        )

        return [_serialize_session_metadata(db, session) for session in sessions]
    finally:
        db.close()


@router.patch("/run-sessions/metadata")
def update_run_session_metadata(payload: RunSessionMetadataUpdate):
    db = SessionLocal()
    try:
        session = (
            db.query(RunSession)
            .filter(
                RunSession.user_id == payload.user_id,
                RunSession.start_time == payload.start_time,
            )
            .first()
        )

        if not session:
            raise HTTPException(status_code=404, detail="Run session not found")

        session.session_type = (
            payload.session_type.strip() if payload.session_type and payload.session_type.strip() else None
        )
        session.session_detail = (
            payload.session_detail.strip() if payload.session_detail and payload.session_detail.strip() else None
        )

        db.commit()
        invalidate_signature(db, payload.user_id)

        db.refresh(session)
        return _serialize_session_metadata(db, session)
    finally:
        db.close()
