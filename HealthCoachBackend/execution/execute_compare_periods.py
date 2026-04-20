from execution.execute_get_metric import execute_get_metric
from execution.execute_period_summary import (
    execute_period_summary,
)
from intents.intents import CompareResult

from execution.execute_period_summary import FULL_SUMMARY_METRICS

from intents.intents import CompareResult
from execution.execute_get_metric import execute_get_metric


def execute_compare_periods(db, user_id, intent: dict):
    print("\n⚙️ EXECUTOR: COMPARE_PERIODS")

    metric = intent["metric"]
    original_message = intent.get("original_message", "")

    left_period = intent.get("period", "this_week")
    right_period = intent.get("compare_period", "last_week")

    # 🔹 Calcul valeur gauche
    left_result = execute_get_metric(
        db,
        user_id,
        {
            "metric": metric,
            "period": left_period,
            "original_message": original_message,
        },
    )

    # 🔹 Calcul valeur droite
    right_result = execute_get_metric(
        db,
        user_id,
        {
            "metric": metric,
            "period": right_period,
            "original_message": original_message,
        },
    )

    delta = left_result.value - right_result.value

    return CompareResult(
        metric=metric,
        aggregation=left_result.aggregation,
        left_period=left_period,
        right_period=right_period,
        left_value=left_result.value,
        right_value=right_result.value,
        delta=delta,
    )
