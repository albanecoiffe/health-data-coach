from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import date
from uuid import UUID

from models.signature import RunnerSignatureModel
from schemas.signature import RunnerSignature


def load_signature(db: Session, user_id: UUID) -> RunnerSignature | None:
    row = (
        db.query(RunnerSignatureModel)
        .filter(RunnerSignatureModel.user_id == user_id)
        .first()
    )

    if not row:
        return None

    return RunnerSignature(**row.signature_json)


def save_signature(
    db: Session,
    user_id: UUID,
    signature: RunnerSignature,
):
    payload = signature.model_dump()

    row = (
        db.query(RunnerSignatureModel)
        .filter(RunnerSignatureModel.user_id == user_id)
        .first()
    )

    if row:
        row.signature_json = payload
        row.period_start = date.fromisoformat(signature.period.start)
        row.period_end = date.fromisoformat(signature.period.end)
        row.weeks = signature.period.weeks
        row.needs_recompute = False
        row.computed_at = func.now()
        row.version = 1
    else:
        row = RunnerSignatureModel(
            user_id=user_id,
            period_start=date.fromisoformat(signature.period.start),
            period_end=date.fromisoformat(signature.period.end),
            weeks=signature.period.weeks,
            signature_json=payload,
            computed_at=func.now(),
            version=1,
            needs_recompute=False,
        )
        db.add(row)

    db.commit()


def invalidate_signature(db: Session, user_id: UUID):
    updated = (
        db.query(RunnerSignatureModel)
        .filter(RunnerSignatureModel.user_id == user_id)
        .update({"needs_recompute": True})
    )

    if updated:
        db.commit()
