from sqlalchemy.orm import Session
from uuid import UUID

from services.signature.signature_store import load_signature, save_signature
from services.signature.builder import build_runner_signature


def get_or_build_signature(db: Session, user_id: UUID):
    signature = load_signature(db, user_id)

    if signature:
        print("🟠 Signature chargée depuis la DB")
        return signature

    print("🟠 Signature recalculée (DB vide)")
    signature = build_runner_signature(db, user_id)
    save_signature(db, user_id, signature)

    return signature
