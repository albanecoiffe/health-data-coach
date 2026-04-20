from uuid import UUID
from sqlalchemy.orm import Session
from datetime import date, datetime

from core.models.signature import RunnerSignatureModel
from schemas.signature import RunnerSignature
from core.services.signature.builder import build_runner_signature


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

    today = date.today()
    current_week = today.isocalendar()[:2]

    record = (
        db.query(RunnerSignatureModel)
        .filter(RunnerSignatureModel.user_id == user_id)
        .one_or_none()
    )

    if record:
        stored_week = record.period_end.isocalendar()[:2]

        if stored_week == current_week and not record.needs_recompute:
            return RunnerSignature.model_validate(record.signature_json)

    # 🔁 rebuild automatique
    signature = build_runner_signature(db=db, user_id=user_id)

    if record:
        record.signature_json = signature.model_dump()
        record.period_start = date.fromisoformat(signature.period.start)
        record.period_end = date.fromisoformat(signature.period.end)
        record.weeks = signature.period.weeks
        record.needs_recompute = False
        record.computed_at = datetime.utcnow()
    else:
        record = RunnerSignatureModel(
            user_id=user_id,
            period_start=date.fromisoformat(signature.period.start),
            period_end=date.fromisoformat(signature.period.end),
            weeks=signature.period.weeks,
            signature_json=signature.model_dump(),
            computed_at=datetime.utcnow(),
            needs_recompute=False,
            version=1,
        )
        db.add(record)

    db.commit()
    return signature
