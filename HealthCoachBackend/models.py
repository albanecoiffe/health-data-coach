# models.py
import uuid
from sqlalchemy import (
    Column,
    Float,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from services.database import Base


class RunSession(Base):
    __tablename__ = "run_sessions"

    # -----------------------------
    # Identité
    # -----------------------------
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    start_time = Column(
        DateTime,
        nullable=False,
        index=True,
    )

    # -----------------------------
    # Données globales
    # -----------------------------
    distance_km = Column(Float)
    duration_min = Column(Float)
    avg_hr = Column(Float)

    # -----------------------------
    # Temps par zone cardiaque (minutes)
    # -----------------------------
    z1_min = Column(Float)
    z2_min = Column(Float)
    z3_min = Column(Float)
    z4_min = Column(Float)
    z5_min = Column(Float)

    # -----------------------------
    # Contraintes
    # -----------------------------
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "start_time",
            name="uq_run_user_start",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<RunSession user={self.user_id} "
            f"start={self.start_time} "
            f"dist={self.distance_km}km>"
        )
