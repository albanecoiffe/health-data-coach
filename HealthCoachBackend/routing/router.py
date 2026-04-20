# endpoint /chat_v2 qui orchestre tout
# routing/router.py

from sqlalchemy.orm import Session
from uuid import UUID

from execution.execute_compare_periods import (
    execute_compare_periods,
)
from execution.execute_get_metric import execute_get_metric
from execution.execute_period_summary import (
    execute_period_summary,
    FULL_SUMMARY_METRICS,
)
from execution.execute_coaching import execute_coaching
from execution.execute_recommendation import (
    execute_recommendation,
)

from normalization.normalizer import (
    normalize_period,
    normalize_metric_from_message,
)

from verbalization.verbalizer import (
    verbalize_metric_llm,
    verbalize_period_comparison_llm,
    verbalize_period_summary_llm,
    verbalize_small_talk_llm,
    verbalize_coaching_llm,
    verbalize_recommendation_llm,
)

from routing.semantic_entrypoint import SemanticEntrypoint
import os

# =====================================================
# INITIALISATION DU PRÉ-ROUTER SÉMANTIQUE (A)
# =====================================================

# DATABASE_URL dans .env

SEMANTIC_ENTRYPOINT = SemanticEntrypoint(connection_string=os.getenv("DATABASE_URL"))


# =====================================================
# 🧭 ROUTER MÉTIER (INCHANGÉ DANS SA LOGIQUE)
# =====================================================


def route_intent(db: Session, user_id, intent: dict):
    print("\n🧭 ROUTER")
    print("➡️ Intent type :", intent.get("intent"))

    session_id: UUID | None = intent.get("session_id")

    # -------------------------------------------------
    # 🧠 PRÉ-ROUTING SÉMANTIQUE (SOLUTION A)
    # -------------------------------------------------
    original_message = intent.get("original_message")
    if not original_message:
        original_message = intent.get("message", "")

    intent = SEMANTIC_ENTRYPOINT.resolve_intent(
        message=original_message,
        base_intent=intent,
    )

    print("🧠 Intent source :", intent.get("_source"))
    print("🧠 Confidence :", intent.get("_confidence"))

    # -------------------------------------------------
    # 🔧 NORMALISATION EXISTANTE
    # -------------------------------------------------
    intent = normalize_metric_from_message(intent)
    print("✅ Normalized intent :", intent)

    # =====================================================
    # GET METRIC
    # =====================================================
    if intent.get("intent") == "GET_METRIC":
        intent = normalize_period(intent)
        result = execute_get_metric(db, user_id, intent)

        reply = verbalize_metric_llm(
            user_message=intent.get("original_message", ""),
            metric=result.metric,
            value=result.value,
            period_key=intent["period"],
        )

        return {
            "type": "ANSWER_NOW",
            "reply": reply,
            "data": result.model_dump(),
        }

    # =====================================================
    # COMPARE PERIODS
    # =====================================================
    if intent.get("intent") == "COMPARE_PERIODS":
        if "period" not in intent and "compare_period" not in intent:
            intent["period"] = "this_week"
            intent["compare_period"] = "last_week"

        intent = normalize_period(intent)

        result = execute_compare_periods(db, user_id, intent)

        reply = verbalize_period_comparison_llm(
            user_message=intent.get("original_message", ""),
            left_period=result.left_period,
            right_period=result.right_period,
            left_value=result.left_value,
            right_value=result.right_value,
            delta=result.delta,
        )

        return {
            "type": "ANSWER_NOW",
            "reply": reply,
            "data": result,
        }

    # =====================================================
    # SUMMARY
    # =====================================================
    if intent.get("intent") == "PERIOD_SUMMARY":
        result = execute_period_summary(
            db,
            user_id,
            intent["period"],
            intent.get("original_message", ""),
            FULL_SUMMARY_METRICS,
        )

        reply = verbalize_period_summary_llm(
            user_message=intent.get("original_message", ""),
            summary=result,
        )

        return {
            "type": "ANSWER_NOW",
            "reply": reply,
            "data": result,
        }

    # =====================================================
    # COACHING
    # =====================================================
    if intent.get("intent") == "COACHING":
        result = execute_coaching(
            db,
            user_id,
            intent,
            intent.get("original_message", ""),
        )

        if result.get("error"):
            return {
                "type": "ANSWER_NOW",
                "reply": result.get(
                    "message", "Je ne peux pas répondre à cette question."
                ),
            }

        reply = verbalize_coaching_llm(
            user_message=intent.get("original_message", ""),
            coaching_type=result["coaching_type"],
            signature=result["signature"],
            facts=result["facts"],
            already_started=False,
        )

        return {
            "type": "ANSWER_NOW",
            "reply": reply,
            "data": {
                "coaching_type": result["coaching_type"],
                "facts": result["facts"],
            },
        }

    # =====================================================
    # RECOMMENDATION
    # =====================================================
    if intent.get("intent") == "RECOMMENDATION":
        reco = execute_recommendation(db, user_id)

        reply = verbalize_recommendation_llm(
            recommendation=reco,
            session_id=session_id,
        )

        return {
            "type": "ANSWER_NOW",
            "reply": reply,
            "data": reco,
        }

    # =====================================================
    # SMALL TALK
    # =====================================================
    if intent.get("intent") == "SMALL_TALK":
        reply = verbalize_small_talk_llm(
            user_message=intent.get("original_message", "")
        )

        return {
            "type": "ANSWER_NOW",
            "reply": reply,
        }

    # =====================================================
    # FALLBACK FINAL
    # =====================================================
    return {
        "type": "ANSWER_NOW",
        "reply": "Je n’ai pas compris ta demande.",
    }
