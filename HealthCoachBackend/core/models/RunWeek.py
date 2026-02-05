import enum
from sqlalchemy import Column, Date, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from database import Base


class RunWeek(Base):
    __tablename__ = "run_weeks"

    user_id = Column(UUID(as_uuid=True), primary_key=True)
    year = Column(Integer, primary_key=True)
    iso_week = Column(Integer, primary_key=True)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    sessions_count = Column(Integer, nullable=False)

    total_distance_km = Column(Float, nullable=False)
    total_duration_min = Column(Float, nullable=False)

    z1_z3_pct = Column(Float, nullable=False)
    z4_z5_pct = Column(Float, nullable=False)

    avg_load = Column(Float, nullable=False)

    created_at = Column(DateTime, server_default=func.now())
