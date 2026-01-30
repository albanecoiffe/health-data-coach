# intent_based_querying/executors/execute_coaching.py

from coaching.dispatcher import detect_coaching_type
from coaching.rules import (
    analyze_regularity,
    analyze_volume,
    analyze_load,
    analyze_progress,
)

from services.signature.signature_service import get_or_build_signature
from intent_based_querying.execution.execute_period_summary import (
    execute_period_summary,
)
from intent_based_querying.intents.intents import CoachingResult


def execute_coaching(db, user_id, intent, user_message):
    # 1️⃣ Charger la signature 52 semaines
    signature = get_or_build_signature(db, user_id)

    if not signature:
        return {
            "error": "NOT_ENOUGH_HISTORY",
            "message": "Je peux t’aider, mais je n’ai pas encore assez d’historique.",
        }

    signature_dict = (
        signature.model_dump() if hasattr(signature, "model_dump") else signature
    )

    # 2️⃣ Déterminer le type de coaching
    coaching_type = detect_coaching_type(user_message)

    if not coaching_type:
        return {
            "error": "UNKNOWN_COACHING_TYPE",
            "message": "Je ne suis pas sûr de ce que tu veux analyser.",
        }

    # 3️⃣ Calcul des facts backend
    if coaching_type == "REGULARITY":
        facts = analyze_regularity(signature_dict)

    elif coaching_type == "PROGRESS":
        facts = analyze_progress(signature_dict)

    elif coaching_type in {"VOLUME", "LOAD"}:
        summary = execute_period_summary(
            db,
            user_id,
            period="THIS_WEEK",
        )

        if coaching_type == "VOLUME":
            facts = analyze_volume(summary, signature_dict)
        else:
            facts = analyze_load(summary, signature_dict)

    else:
        return {
            "error": "UNSUPPORTED_COACHING_TYPE",
            "message": "Je ne suis pas sûr de ce que tu veux analyser.",
        }

    if not facts:
        return {
            "error": "NO_FACTS",
            "message": "Je n’ai pas assez de données pour répondre.",
        }

    # 4️⃣ Payload final (DICT, TOUJOURS)
    return {
        "coaching_type": coaching_type,
        "signature": signature_dict,
        "facts": facts,
    }
