from sqlalchemy.orm import Session
from models.signature import RunnerSignatureModel
from schemas.signature import RunnerSignature
from uuid import UUID


def load_signature(db: Session, user_id: UUID) -> RunnerSignature | None:
    row = (
        db.query(RunnerSignatureModel)
        .filter(RunnerSignatureModel.user_id == user_id)
        .first()
    )

    if not row:
        return None

    return RunnerSignature(**row.signature_json)


from datetime import date


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
    else:
        row = RunnerSignatureModel(
            user_id=user_id,
            period_start=date.fromisoformat(signature.period.start),
            period_end=date.fromisoformat(signature.period.end),
            weeks=signature.period.weeks,
            signature_json=payload,
        )
        db.add(row)

    db.commit()


def invalidate_signature(db: Session, user_id: UUID):
    (
        db.query(RunnerSignatureModel)
        .filter(RunnerSignatureModel.user_id == user_id)
        .update({"needs_recompute": True})
    )
    db.commit()
