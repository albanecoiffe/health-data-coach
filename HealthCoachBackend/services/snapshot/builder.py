from models.RunSession import RunSession
from schemas.schemas import (
    WeeklySnapshot,
    WeeklyTotals,
    TrainingLoad,
    Period,
    DailyRun,
)
from sqlalchemy.orm import Session
from datetime import datetime

from services.snapshot.metrics import (
    compute_totals,
    compute_zones_percent,
    compute_training_load,
)


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
    # 2️⃣ Cas vide
    # --------------------------------------------------
    if not sessions:
        return WeeklySnapshot(
            week_label="Custom period",
            period=Period(
                start=start.date().isoformat(),
                end=end.date().isoformat(),
            ),
            totals=WeeklyTotals(
                distance_km=0.0,
                duration_min=0.0,
                sessions=0,
                elevation_m=0.0,
                avg_hr=None,
            ),
            zones_percent={},
            daily_runs=[],
            training_load=None,
            comparison_prev_week=None,
        )

    # --------------------------------------------------
    # 3️⃣ Daily runs (transport ONLY)
    # --------------------------------------------------
    daily_runs = [
        DailyRun(
            date=s.start_time.isoformat(),
            distance_km=s.distance_km,
            duration_min=s.duration_min,
            elevation_m=s.elevation_m or 0.0,
            avg_hr=s.avg_hr or 0.0,
            z1=s.z1_min,
            z2=s.z2_min,
            z3=s.z3_min,
            z4=s.z4_min,
            z5=s.z5_min,
        )
        for s in sessions
    ]

    # --------------------------------------------------
    # 4️⃣ Calculs (via metrics)
    # --------------------------------------------------
    totals_data = compute_totals(sessions)
    zones_percent = compute_zones_percent(sessions)
    load_7d = compute_training_load(sessions)

    # --------------------------------------------------
    # 5️⃣ Assemblage schemas
    # --------------------------------------------------
    totals = WeeklyTotals(**totals_data)

    training_load = TrainingLoad(
        load_7d=load_7d,
        load_28d=0.0,  # calculé plus tard
        ratio=0.0,  # calculé plus tard
    )

    # --------------------------------------------------
    # 6️⃣ Snapshot final
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
