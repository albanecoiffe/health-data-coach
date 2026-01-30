from sqlalchemy.orm import Session
from uuid import UUID

from services.signature.signature_store import load_signature, save_signature
from services.signature.builder import build_runner_signature
from datetime import date


def get_or_build_signature(db: Session, user_id):
    """
    Retourne la signature depuis Neon si elle est valide,
    sinon la reconstruit et la sauvegarde.
    """

    stored = load_signature(db, user_id)

    today = date.today()
    current_week = today.isocalendar()[:2]  # (year, week)

    # ✅ Cas 1 : signature existante
    if stored:
        print("🧠 Signature chargée depuis Neon")
        period_end = date.fromisoformat(stored.period.end)
        stored_week = period_end.isocalendar()[:2]

        # même semaine → on la réutilise
        if stored_week == current_week:
            return stored

    # ❌ Cas 2 : absente ou obsolète → rebuild
    signature = build_runner_signature(db, user_id)
    save_signature(db, user_id, signature)

    return signature
