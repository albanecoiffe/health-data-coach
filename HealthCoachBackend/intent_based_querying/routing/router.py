# endpoint /chat_v2 qui orchestre tout
# app/v2/router.py
from sqlalchemy.orm import Session
from uuid import UUID

from intent_based_querying.execution.execute_compare_periods import (
    execute_compare_periods,
)
from intent_based_querying.execution.execute_get_metric import execute_get_metric
from intent_based_querying.execution.execute_period_summary import (
    execute_period_summary,
    FULL_SUMMARY_METRICS,
)
from intent_based_querying.execution.execute_coaching import execute_coaching

from intent_based_querying.normalization.normalizer import (
    normalize_period,
    normalize_metric_from_message,
)
from intent_based_querying.verbalization.verbalizer import (
    verbalize_metric_llm,
    verbalize_period_comparison_llm,
    verbalize_period_summary_llm,
    verbalize_small_talk_llm,
    verbalize_coaching_llm,
    verbalize_recommendation_llm,
)
from intent_based_querying.execution.execute_recommendation import (
    execute_recommendation,
)


def route_intent(db, user_id, intent: dict):
    print("\n🧭 ROUTER")
    print("➡️ Intent type :", intent.get("intent"))

    session_id: UUID | None = intent.get("session_id")

    intent = normalize_metric_from_message(intent)

    print("✅ Normalized intent :", intent)

    # =====================================================
    # GET METRIC
    # =====================================================
    if intent.get("intent") == "GET_METRIC":
        intent = normalize_period(intent)
        result = execute_get_metric(db, user_id, intent)

        print("🗣️ CALLING VERBALIZER")

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
        intent = normalize_period(intent)
        result = execute_compare_periods(db, user_id, intent)

        reply = verbalize_period_comparison_llm(
            user_message=intent.get("original_message", ""),
            left_period=result["left_period"],
            right_period=result["right_period"],
            left=result["left"],
            right=result["right"],
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

        # Erreurs métier
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
    if intent["intent"] == "RECOMMENDATION":
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

    return {
        "type": "ANSWER_NOW",
        "reply": "Je n’ai pas compris ta demande.",
    }
