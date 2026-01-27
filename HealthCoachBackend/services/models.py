from sqlalchemy import Column, DateTime, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID


class RunSession(Base):
    __tablename__ = "run_sessions"

    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, index=True)
    start_time = Column(DateTime, index=True)
    distance_km = Column(Float)
    duration_min = Column(Float)
    avg_hr = Column(Float)
    z1_min = Column(Float)
    z2_min = Column(Float)
    z3_min = Column(Float)
    z4_min = Column(Float)
    z5_min = Column(Float)

    __table_args__ = (UniqueConstraint("user_id", "start_time"),)
