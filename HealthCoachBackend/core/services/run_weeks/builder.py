from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from core.models.RunSession import RunSession
from core.models.RunWeek import RunWeek
from core.heart_rate_zones import high_intensity_minutes, low_intensity_minutes
from database import SessionLocal


def _week_key_for_day(day: date) -> tuple[int, int]:
    year, iso_week, _ = day.isocalendar()
    return year, iso_week


def _week_bounds(year: int, iso_week: int) -> tuple[date, date]:
    return (
        date.fromisocalendar(year, iso_week, 1),
        date.fromisocalendar(year, iso_week, 7),
    )


def _normalize_day(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise TypeError(f"Unsupported touched date value: {value!r}")


def _upsert_run_week(db: Session, user_id, year: int, iso_week: int) -> None:
    week_start, week_end = _week_bounds(year, iso_week)
    start_dt = datetime.combine(week_start, time.min)
    end_dt = datetime.combine(week_end + timedelta(days=1), time.min)

    runs = (
        db.query(RunSession)
        .filter(
            RunSession.user_id == user_id,
            RunSession.start_time >= start_dt,
            RunSession.start_time < end_dt,
        )
        .order_by(RunSession.start_time.asc())
        .all()
    )

    row = (
        db.query(RunWeek)
        .filter(
            RunWeek.user_id == user_id,
            RunWeek.year == year,
            RunWeek.iso_week == iso_week,
        )
        .first()
    )

    if not runs:
        if row:
            db.delete(row)
        return

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
        r.duration_min * (1 + 2 * (high_intensity_minutes(r) / max(r.duration_min, 1)))
        for r in runs
    )

    sessions_count = len(runs)

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
        db.add(
            RunWeek(
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
        )


def build_run_weeks(db: Session, user_id, touched_dates: Iterable[Any] | None = None):
    """Agrège RunSession en RunWeek, avec option de recalcul ciblé par semaines touchées."""
    if touched_dates is None:
        sessions = (
            db.query(RunSession)
            .filter(RunSession.user_id == user_id)
            .order_by(RunSession.start_time.asc())
            .all()
        )
        week_keys = {
            _week_key_for_day(session.start_time.date())
            for session in sessions
        }
    else:
        week_keys = {
            _week_key_for_day(_normalize_day(day))
            for day in touched_dates
        }

    if not week_keys:
        return

    for year, iso_week in sorted(week_keys):
        _upsert_run_week(db, user_id, year, iso_week)

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
