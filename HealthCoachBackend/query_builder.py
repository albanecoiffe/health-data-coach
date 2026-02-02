# intent -> SQLAlchemy statement (contrôlé)


from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from models.RunSession import RunSession
from routing.registry import METRICS


def query_metric(
    db: Session,
    user_id: UUID,
    metric: str,
    start: datetime,
    end: datetime,
) -> float:
    metric = metric.upper()

    if metric not in METRICS:
        raise ValueError(f"Unsupported metric: {metric}")

    config = METRICS[metric]

    stmt = (
        select(config["aggregation"](config["column"]))
        .where(RunSession.user_id == user_id)
        .where(RunSession.start_time >= start)
        .where(RunSession.start_time < end)
    )

    result = db.execute(stmt).scalar()

    return result or 0.0
