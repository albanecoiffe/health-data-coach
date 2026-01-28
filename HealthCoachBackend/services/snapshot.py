from models.models import RunSession
from schemas.schemas import (
    Snapshot,
    SnapshotBatchPayload,
    WeeklySnapshot,
    WeeklyTotals,
    TrainingLoad,
    Period,
    DailyRun,
)
from sqlalchemy.orm import Session
from datetime import datetime

# ======================================================
# SNAPSHOT DEPUIS LA BASE
# build_snapshot_from_db = logique métier + DB
# ======================================================


def build_snapshot_from_db(
    db: Session,
    user_id,
    start: datetime,
    end: datetime,
) -> WeeklySnapshot:
    """
    Construit un WeeklySnapshot STRICTEMENT à partir de la DB
    """

    # --------------------------------------------------
    # 1️⃣ Charger les sessions
    # --------------------------------------------------
    sessions = (
        db.query(RunSession)
        .filter(
            RunSession.user_id == user_id,
            RunSession.start_time >= start,
            RunSession.start_time < end,
        )
        .order_by(RunSession.start_time.asc())
        .all()
    )

    # --------------------------------------------------
    # 2️⃣ Cas vide (IMPORTANT)
    # --------------------------------------------------
    if not sessions:
        return WeeklySnapshot(
            week_label="Custom period",
            period=Period(
                start=start.date().isoformat(),
                end=end.date().isoformat(),
            ),
            totals=WeeklyTotals(
                distance_km=0,
                duration_min=0,
                sessions=0,
                elevation_m=0,
                avg_hr=None,
            ),
            zones_percent={},
            daily_runs=[],
            training_load=None,
            comparison_prev_week=None,
        )

    # --------------------------------------------------
    # 3️⃣ Daily runs
    # --------------------------------------------------
    daily_runs: list[DailyRun] = []

    for s in sessions:
        daily_runs.append(
            DailyRun(
                date=s.start_time.isoformat(),
                distance_km=s.distance_km,
                duration_min=s.duration_min,
                elevation_m=s.elevation_m or 0,
                avg_hr=s.avg_hr or 0,
                z1=s.z1_min,
                z2=s.z2_min,
                z3=s.z3_min,
                z4=s.z4_min,
                z5=s.z5_min,
            )
        )

    # --------------------------------------------------
    # 4️⃣ Totaux
    # --------------------------------------------------
    total_distance = sum(s.distance_km for s in sessions)
    total_duration = sum(s.duration_min for s in sessions)
    total_elevation = sum((s.elevation_m or 0) for s in sessions)

    hr_values = [s.avg_hr for s in sessions if s.avg_hr is not None]
    avg_hr = sum(hr_values) / len(hr_values) if hr_values else None

    totals = WeeklyTotals(
        distance_km=total_distance,
        duration_min=total_duration,
        sessions=len(sessions),
        elevation_m=total_elevation,
        avg_hr=avg_hr,
    )

    # --------------------------------------------------
    # 5️⃣ Zones (%)
    # --------------------------------------------------
    z1 = sum(s.z1_min for s in sessions)
    z2 = sum(s.z2_min for s in sessions)
    z3 = sum(s.z3_min for s in sessions)
    z4 = sum(s.z4_min for s in sessions)
    z5 = sum(s.z5_min for s in sessions)

    total_zone_time = z1 + z2 + z3 + z4 + z5

    zones_percent = {}
    if total_zone_time > 0:
        zones_percent = {
            "z1": z1 / total_zone_time,
            "z2": z2 / total_zone_time,
            "z3": z3 / total_zone_time,
            "z4": z4 / total_zone_time,
            "z5": z5 / total_zone_time,
        }

    # --------------------------------------------------
    # 6️⃣ Training load (simple, cohérent avec Swift)
    # --------------------------------------------------
    load = 0.0
    for s in sessions:
        intense = (s.z4_min + s.z5_min) / max(s.duration_min, 1)
        load += s.duration_min * (1 + 2 * intense)

    training_load = TrainingLoad(
        load_7d=load,
        load_28d=0.0,
        ratio=0.0,
    )

    # --------------------------------------------------
    # 7️⃣ Snapshot final
    # --------------------------------------------------
    return WeeklySnapshot(
        week_label="Custom period",
        period=Period(
            start=start.date().isoformat(),
            end=end.date().isoformat(),
        ),
        totals=totals,
        zones_percent=zones_percent,
        daily_runs=daily_runs,
        training_load=training_load,
        comparison_prev_week=None,
    )
