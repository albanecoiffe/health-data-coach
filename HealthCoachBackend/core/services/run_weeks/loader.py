from sqlalchemy.orm import Session
from core.models.RunWeek import RunWeek


def load_run_weeks(db: Session, user_id):
    """
    Charge toutes les semaines complètes (déjà agrégées en SQL)
    """
    return (
        db.query(RunWeek)
        .filter(RunWeek.user_id == user_id)
        .order_by(RunWeek.year, RunWeek.iso_week)
        .all()
    )
