from sqlalchemy.orm import Session
from uuid import UUID

from services.signature_store import load_signature, save_signature
from services.signature_builder import build_runner_signature


def get_or_build_signature(db: Session, user_id: UUID):
    signature = load_signature(db, user_id)

    if signature:
        return signature

    signature = build_runner_signature(db, user_id)
    save_signature(db, user_id, signature)

    return signature
