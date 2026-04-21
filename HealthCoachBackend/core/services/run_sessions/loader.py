from sqlalchemy.orm import Session

from core.heart_rate_zones import high_intensity_minutes, low_intensity_minutes
from core.models.RunSession import RunSession


def load_run_sessions(db: Session, user_id):
    sessions = db.query(RunSession).filter(RunSession.user_id == user_id).all()

    out = []

    for s in sessions:
        # -----------------------------
        # 1️⃣ Nettoyage valeurs brutes
        # -----------------------------
        distance = float(s.distance_km) if s.distance_km else 0.0
        duration = float(s.duration_min) if s.duration_min else 0.0

        # -----------------------------
        # 2️⃣ Features dérivées
        # -----------------------------
        pace = (duration / distance) if distance > 0 and duration > 0 else None

        low_pct = low_intensity_minutes(s) / duration if duration > 0 else 0.0
        high_pct = high_intensity_minutes(s) / duration if duration > 0 else 0.0

        out.append(
            {
                "start_time": s.start_time,
                "distance_km": distance if distance > 0 else None,
                "duration_min": duration if duration > 0 else None,
                "pace_min_per_km": pace,
                "low_intensity_pct": low_pct,
                "high_intensity_pct": high_pct,
            }
        )

    return out
