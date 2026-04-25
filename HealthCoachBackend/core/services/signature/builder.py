from sqlalchemy.orm import Session
import pandas as pd

from core.models.RunSession import RunSession
from schemas.signature import RunnerSignature
from core.services.signature.analysis import build_runner_signature_from_dataframe


def build_runner_signature(db: Session, user_id) -> RunnerSignature:
    """
    Construit la signature long-terme du coureur
    sur une fenêtre glissante de 52 semaines,
    en excluant la semaine ISO en cours des trends.
    """
    print("🔥 build_runner_signature START")
    all_sessions = (
        db.query(RunSession)
        .filter(RunSession.user_id == user_id)
        .order_by(RunSession.start_time.asc())
        .all()
    )

    if not all_sessions:
        raise ValueError("No run sessions found for user")

    sessions_df = pd.DataFrame(
        [
            {
                "start_time": session.start_time,
                "distance_km": session.distance_km,
                "duration_min": session.duration_min,
                "avg_hr": session.avg_hr,
                "elevation_m": session.elevation_m,
                "active_kcal": session.active_kcal,
                "z1_min": session.z1_min,
                "z2_min": session.z2_min,
                "z3_min": session.z3_min,
                "z4_min": session.z4_min,
                "z5_min": session.z5_min,
            }
            for session in all_sessions
        ]
    )
    signature, _ = build_runner_signature_from_dataframe(sessions_df)
    return signature
