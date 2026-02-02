from execution.execute_get_metric import execute_get_metric
from intents.intents import PeriodSummaryResult
from normalization.time_resolver import (
    normalize_period_with_original_message,
    serialize_period,
)


FULL_SUMMARY_METRICS = [
    "sessions",
    "distance_km",
    "duration_min",
    "avg_hr",
    "elevation_m",
    "active_kcal",
]


def execute_period_summary(
    db,
    user_id,
    period,
    original_message: str,
    metrics: list[str],
):
    # ✅ NORMALISATION AVANT TOUT
    period = normalize_period_with_original_message(period, original_message)

    summary = {}

    for metric in metrics:
        metric_intent = {
            "metric": metric,
            "period": period,  # ← period NORMALISÉ
        }

        result = execute_get_metric(db, user_id, metric_intent)
        summary[metric] = result.value

    return PeriodSummaryResult(
        period=serialize_period(period),  # ✅ string
        sessions=summary["sessions"],
        distance_km=summary["distance_km"],
        duration_min=summary["duration_min"],
        avg_hr=summary["avg_hr"],
        elevation_m=summary["elevation_m"],
        active_kcal=summary["active_kcal"],
    )
