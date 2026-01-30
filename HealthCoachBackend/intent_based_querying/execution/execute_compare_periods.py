from intent_based_querying.execution.execute_get_metric import execute_get_metric
from intent_based_querying.execution.execute_period_summary import (
    execute_period_summary,
)
from intent_based_querying.intents.intents import CompareResult


def execute_compare_periods(db, user_id, intent: dict):
    print("\n⚙️ EXECUTOR: COMPARE_PERIODS")

    left_period = intent["period"]
    right_period = intent["compare_period"]

    left_summary = execute_period_summary(db, user_id, left_period)
    right_summary = execute_period_summary(db, user_id, right_period)

    return {
        "left_period": left_period,
        "right_period": right_period,
        "left": left_summary,
        "right": right_summary,
    }
