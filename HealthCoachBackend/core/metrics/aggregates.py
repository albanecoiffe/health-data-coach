from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from datetime import datetime

from core.models.RunSession import RunSession


def get_aggregated_totals(
    db: Session,
    user_id: UUID,
    start: datetime,
    end: datetime,
) -> dict:
    """
    Agrégation DB des séances de course pour une période donnée.

    Retourne un dict normalisé :
    {
        distance_km: float,
        duration_min: float,
        sessions: int,
        elevation_m: float,
        avg_hr: float | None
    }
    """

    q = (
        db.query(
            func.count(RunSession.id).label("sessions"),
            func.coalesce(func.sum(RunSession.distance_km), 0.0).label("distance_km"),
            func.coalesce(func.sum(RunSession.duration_min), 0.0).label("duration_min"),
            func.coalesce(func.sum(RunSession.elevation_m), 0.0).label("elevation_m"),
            func.avg(RunSession.avg_hr).label("avg_hr"),
        )
        .filter(RunSession.user_id == user_id)
        .filter(RunSession.start_time >= start)
        .filter(RunSession.start_time < end)
    )

    result = q.one()

    return {
        "distance_km": float(result.distance_km or 0.0),
        "duration_min": float(result.duration_min or 0.0),
        "sessions": int(result.sessions or 0),
        "elevation_m": float(result.elevation_m or 0.0),
        "avg_hr": float(result.avg_hr) if result.avg_hr is not None else None,
    }
