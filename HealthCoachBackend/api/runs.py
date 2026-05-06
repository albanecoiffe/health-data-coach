# import
from fastapi import APIRouter, HTTPException, Query, Request
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from api.auth import assert_import_token
from database import SessionLocal
from core.models.RunSession import RunSession
from core.models.RunSessionMergeAlias import RunSessionMergeAlias
from schemas.schemas import RunSessionCreate, RunSessionMergeRequest, RunSessionMetadataUpdate
from core.services.signature.signature_store import invalidate_signature
from core.services.run_weeks.builder import build_run_weeks
from core.services.run_sessions.loader import load_run_sessions
from core.services.session_type_predictor import build_session_type_predictor

router = APIRouter(prefix="/api")


def _create_run_session_from_payload(payload: RunSessionCreate) -> RunSession:
    return RunSession(
        user_id=payload.user_id,
        start_time=payload.start_time,
        merged_into_start_time=None,
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
    aliased_source = (
        db.query(RunSessionMergeAlias.id)
        .filter(
            RunSessionMergeAlias.user_id == payload.user_id,
            RunSessionMergeAlias.source_start_time == payload.start_time,
        )
        .first()
        is not None
    )
    if aliased_source:
        return "duplicate"

    existing = (
        db.query(RunSession)
        .filter(
            RunSession.user_id == payload.user_id,
            RunSession.start_time == payload.start_time,
        )
        .first()
    )

    if existing:
        has_merged_children = (
            db.query(RunSession.id)
            .filter(
                RunSession.user_id == payload.user_id,
                RunSession.merged_into_start_time == payload.start_time,
            )
            .first()
            is not None
        )
        has_merge_alias_children = (
            db.query(RunSessionMergeAlias.id)
            .filter(
                RunSessionMergeAlias.user_id == payload.user_id,
                RunSessionMergeAlias.target_start_time == payload.start_time,
            )
            .first()
            is not None
        )
        if has_merged_children or has_merge_alias_children:
            return "duplicate"
        if _session_matches_payload(existing, payload):
            return "duplicate"
        _apply_payload_to_session(existing, payload)
        db.commit()
        return "updated"

    db.add(_create_run_session_from_payload(payload))
    db.commit()
    return "inserted"


def _serialize_session_metadata(
    session: RunSession,
    predictor=None,
) -> dict:
    predicted = None
    if not session.session_type:
        if predictor is not None:
            predicted = predictor(session)

    effective = session.session_type or predicted

    return {
        "start_time": session.start_time.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "merged_into_start_time": (
            session.merged_into_start_time.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
            if session.merged_into_start_time
            else None
        ),
        "session_type": session.session_type,
        "predicted_session_type": predicted,
        "effective_session_type": effective,
        "session_detail": session.session_detail,
    }


def _serialize_merge_alias_metadata(alias: RunSessionMergeAlias) -> dict:
    return {
        "start_time": alias.source_start_time.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "merged_into_start_time": alias.target_start_time.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "session_type": None,
        "predicted_session_type": None,
        "effective_session_type": None,
        "session_detail": None,
    }


def _merge_two_run_sessions(primary: RunSession, secondary: RunSession) -> None:
    primary_distance = float(primary.distance_km or 0.0)
    secondary_distance = float(secondary.distance_km or 0.0)
    primary_duration = float(primary.duration_min or 0.0)
    secondary_duration = float(secondary.duration_min or 0.0)
    total_duration = primary_duration + secondary_duration

    weighted_hr_sum = 0.0
    if primary.avg_hr is not None:
        weighted_hr_sum += float(primary.avg_hr) * primary_duration
    if secondary.avg_hr is not None:
        weighted_hr_sum += float(secondary.avg_hr) * secondary_duration

    primary.distance_km = primary_distance + secondary_distance
    primary.duration_min = total_duration
    primary.avg_hr = (weighted_hr_sum / total_duration) if total_duration > 0 else primary.avg_hr
    primary.elevation_m = float(primary.elevation_m or 0.0) + float(secondary.elevation_m or 0.0)
    primary.active_kcal = float(primary.active_kcal or 0.0) + float(secondary.active_kcal or 0.0)
    primary.z1_min = float(primary.z1_min or 0.0) + float(secondary.z1_min or 0.0)
    primary.z2_min = float(primary.z2_min or 0.0) + float(secondary.z2_min or 0.0)
    primary.z3_min = float(primary.z3_min or 0.0) + float(secondary.z3_min or 0.0)
    primary.z4_min = float(primary.z4_min or 0.0) + float(secondary.z4_min or 0.0)
    primary.z5_min = float(primary.z5_min or 0.0) + float(secondary.z5_min or 0.0)

    if not (primary.session_type and primary.session_type.strip()):
        primary.session_type = secondary.session_type
    if not (primary.session_detail and primary.session_detail.strip()):
        primary.session_detail = secondary.session_detail

    primary.merged_into_start_time = None
    secondary.merged_into_start_time = primary.start_time


def _match_session_by_start_time(
    sessions: list[RunSession],
    target_start_time: datetime,
    excluded_ids: set | None = None,
    tolerance_seconds: int = 180,
) -> RunSession | None:
    def _as_utc_naive(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    excluded_ids = excluded_ids or set()
    target_utc_naive = _as_utc_naive(target_start_time)
    candidates = [
        session for session in sessions
        if session.id not in excluded_ids
        and abs((_as_utc_naive(session.start_time) - target_utc_naive).total_seconds()) <= tolerance_seconds
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda session: abs((_as_utc_naive(session.start_time) - target_utc_naive).total_seconds()),
    )


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
        merge_aliases = (
            db.query(RunSessionMergeAlias)
            .filter(
                RunSessionMergeAlias.user_id == user_id,
                RunSessionMergeAlias.source_start_time >= start_dt,
                RunSessionMergeAlias.source_start_time < end_dt,
            )
            .order_by(RunSessionMergeAlias.source_start_time.asc())
            .all()
        )

        predictor = build_session_type_predictor(db, user_id)
        return [
            *[_serialize_session_metadata(session, predictor=predictor) for session in sessions],
            *[_serialize_merge_alias_metadata(alias) for alias in merge_aliases],
        ]
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
        predictor = build_session_type_predictor(db, payload.user_id)
        return _serialize_session_metadata(session, predictor=predictor)
    finally:
        db.close()


@router.post("/run-sessions/merge")
def merge_run_sessions(payload: RunSessionMergeRequest):
    db = SessionLocal()
    try:
        if payload.primary_start_time == payload.secondary_start_time:
            raise HTTPException(status_code=400, detail="Cannot merge the same session twice")

        primary, secondary = sorted(
            [payload.primary_start_time, payload.secondary_start_time]
        )

        tolerance = timedelta(minutes=3)
        sessions = (
            db.query(RunSession)
            .filter(
                RunSession.user_id == payload.user_id,
                RunSession.start_time >= primary - tolerance,
                RunSession.start_time <= secondary + tolerance,
            )
            .order_by(RunSession.start_time.asc())
            .all()
        )

        if len(sessions) != 2:
            raise HTTPException(status_code=404, detail="Run sessions not found in merge window")

        primary_session = _match_session_by_start_time(sessions, primary)
        if primary_session is None:
            raise HTTPException(status_code=404, detail="Primary run session not found")

        secondary_session = _match_session_by_start_time(
            sessions,
            secondary,
            excluded_ids={primary_session.id},
        )
        if secondary_session is None:
            raise HTTPException(status_code=404, detail="Secondary run session not found")

        if primary_session.merged_into_start_time is not None or secondary_session.merged_into_start_time is not None:
            raise HTTPException(status_code=400, detail="One of the sessions is already merged")

        _merge_two_run_sessions(primary_session, secondary_session)
        merge_alias = RunSessionMergeAlias(
            user_id=payload.user_id,
            source_start_time=secondary_session.start_time,
            target_start_time=primary_session.start_time,
        )
        db.add(merge_alias)
        db.delete(secondary_session)
        db.commit()

        build_run_weeks(db, payload.user_id, touched_dates=[primary, secondary])
        invalidate_signature(db, payload.user_id)
        predictor = build_session_type_predictor(db, payload.user_id)
        db.refresh(primary_session)

        return [
            _serialize_session_metadata(primary_session, predictor=predictor),
            _serialize_merge_alias_metadata(merge_alias),
        ]
    finally:
        db.close()
