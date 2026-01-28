from uuid import UUID
from sqlalchemy.orm import Session
from datetime import date

from models.signature import RunnerSignatureModel
from schemas.signature import RunnerSignature
from services.signature.builder import build_runner_signature


def get_signature_from_store(
    db: Session,
    user_id: UUID,
) -> RunnerSignature:
    """
    Source of truth pour la runner signature.

    Règles :
    - si absente → calcul + persist
    - si marquée needs_recompute → recalcul
    - sinon → lecture DB
    """

    record = (
        db.query(RunnerSignatureModel)
        .filter(RunnerSignatureModel.user_id == user_id)
        .one_or_none()
    )

    if record and not record.needs_recompute:
        # ✅ lecture simple
        return RunnerSignature.model_validate(record.signature_json)

    # 🔁 recalcul
    signature = build_runner_signature(db=db, user_id=user_id)

    if record:
        record.signature_json = signature.model_dump()
        record.period_start = date.fromisoformat(signature.period.start)
        record.period_end = date.fromisoformat(signature.period.end)
        record.weeks = signature.period.weeks
        record.needs_recompute = False
    else:
        record = RunnerSignatureModel(
            user_id=user_id,
            period_start=date.fromisoformat(signature.period.start),
            period_end=date.fromisoformat(signature.period.end),
            weeks=signature.period.weeks,
            signature_json=signature.model_dump(),
        )
        db.add(record)

    db.commit()

    return signature
