from datetime import date
from core.models.RunSession import RunSession


def get_current_week_sessions(db, user_id):
    today = date.today()
    year, week, _ = today.isocalendar()

    sessions = db.query(RunSession).filter(RunSession.user_id == user_id).all()

    return [
        s for s in sessions if s.start_time.date().isocalendar()[:2] == (year, week)
    ]
