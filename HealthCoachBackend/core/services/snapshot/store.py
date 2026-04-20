from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session

from schemas.schemas import WeeklySnapshot
from core.services.snapshot.builder import build_snapshot_from_db


def get_snapshot_from_store(
    db: Session,
    user_id: UUID,
    start: datetime,
    end: datetime,
) -> WeeklySnapshot:
    """
    Façade de lecture snapshot.

    V1 :
    - pas de cache
    - pas de persistance
    - calcul à la demande

    V2 :
    - possible cache (redis / table)
    - invalidation sur nouvelle RunSession
    """
    return build_snapshot_from_db(
        db=db,
        user_id=user_id,
        start=start,
        end=end,
    )
