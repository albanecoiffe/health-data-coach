from sqlalchemy import Column, Date, DateTime, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database import Base


class RunnerSignatureModel(Base):
    __tablename__ = "runner_signatures"

    user_id = Column(UUID(as_uuid=True), primary_key=True)

    computed_at = Column(DateTime, server_default=func.now(), nullable=False)

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    weeks = Column(Integer, nullable=False)

    signature_json = Column(JSONB, nullable=False)

    version = Column(Integer, default=1, nullable=False)
    needs_recompute = Column(Boolean, default=False, nullable=False)
