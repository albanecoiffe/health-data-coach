import uuid

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class RunSessionMergeAlias(Base):
    __tablename__ = "run_session_merge_aliases"

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

    source_start_time = Column(
        DateTime,
        nullable=False,
        index=True,
    )

    target_start_time = Column(
        DateTime,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "source_start_time",
            name="uq_run_merge_alias_user_source",
        ),
    )
