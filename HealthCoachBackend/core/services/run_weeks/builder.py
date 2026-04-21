from sqlalchemy.orm import Session
from datetime import timedelta, date

from core.models.RunSession import RunSession
from core.models.RunWeek import RunWeek
from core.heart_rate_zones import high_intensity_minutes, low_intensity_minutes
from database import SessionLocal


def build_run_weeks(db: Session, user_id):
    """
    Agrège toutes les RunSession en RunWeek (ISO weeks).
    Idempotent : peut être relancé sans effet de bord.
    """

    sessions = (
        db.query(RunSession)
        .filter(RunSession.user_id == user_id)
        .order_by(RunSession.start_time.asc())
        .all()
    )

    if not sessions:
        return

    # -----------------------------
    # 1️⃣ Grouper par semaine ISO
    # -----------------------------
    weeks = {}

    for s in sessions:
        year, iso_week, _ = s.start_time.date().isocalendar()
        weeks.setdefault((year, iso_week), []).append(s)

    # -----------------------------
    # 2️⃣ Construire / upsert chaque semaine
    # -----------------------------
    for (year, iso_week), runs in weeks.items():
        start_date = min(r.start_time.date() for r in runs)
        end_date = max(r.start_time.date() for r in runs)

        total_distance = sum(r.distance_km for r in runs)
        total_duration = sum(r.duration_min for r in runs)

        z1z3 = sum(low_intensity_minutes(r) for r in runs)
        z4z5 = sum(high_intensity_minutes(r) for r in runs)

        z_total = z1z3 + z4z5

        z4z5_pct = z4z5 / z_total if z_total > 0 else 0.0
        z1z3_pct = 1.0 - z4z5_pct

        avg_load = sum(
            r.duration_min
            * (1 + 2 * (high_intensity_minutes(r) / max(r.duration_min, 1)))
            for r in runs
        )

        sessions_count = len(runs)

        # -----------------------------
        # 3️⃣ UPSERT
        # -----------------------------
        row = (
            db.query(RunWeek)
            .filter(
                RunWeek.user_id == user_id,
                RunWeek.year == year,
                RunWeek.iso_week == iso_week,
            )
            .first()
        )

        if row:
            row.start_date = start_date
            row.end_date = end_date
            row.sessions_count = sessions_count
            row.total_distance_km = total_distance
            row.total_duration_min = total_duration
            row.z1_z3_pct = z1z3_pct
            row.z4_z5_pct = z4z5_pct
            row.avg_load = avg_load
        else:
            row = RunWeek(
                user_id=user_id,
                year=year,
                iso_week=iso_week,
                start_date=start_date,
                end_date=end_date,
                sessions_count=sessions_count,
                total_distance_km=total_distance,
                total_duration_min=total_duration,
                z1_z3_pct=z1z3_pct,
                z4_z5_pct=z4z5_pct,
                avg_load=avg_load,
            )
            db.add(row)

    db.commit()


def rebuild_run_weeks_if_empty():
    db = SessionLocal()

    try:
        count = db.query(RunWeek).count()

        if count > 0:
            print("🟢 RunWeek already populated — skipping rebuild")
            return

        print("🔁 RunWeek empty — rebuilding from RunSession")

        user_ids = db.query(RunSession.user_id).distinct().all()

        for (user_id,) in user_ids:
            print("➡️ rebuilding weeks for user:", user_id)
            build_run_weeks(db, user_id)

        print("✅ RunWeek rebuild completed")

    finally:
        db.close()
