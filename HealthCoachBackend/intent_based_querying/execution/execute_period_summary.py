from intent_based_querying.execution.execute_get_metric import execute_get_metric
from intent_based_querying.intents.intents import PeriodSummaryResult

FULL_SUMMARY_METRICS = [
    "sessions",
    "distance_km",
    "duration_min",
    "avg_hr",
    "elevation_m",
    "active_kcal",
]


def execute_period_summary(db, user_id, period: str, metrics: list[str]):
    """
    Calcule un résumé d'une période pour une liste de métriques donnée.
    """

    summary = {}

    for metric in metrics:
        metric_intent = {
            "metric": metric,
            "period": period,
        }

        result = execute_get_metric(db, user_id, metric_intent)
        summary[metric] = result.value

    return PeriodSummaryResult(
        period=period,
        sessions=summary["sessions"],
        distance_km=summary["distance_km"],
        duration_min=summary["duration_min"],
        avg_hr=summary["avg_hr"],
        elevation_m=summary["elevation_m"],
        active_kcal=summary["active_kcal"],
    )
