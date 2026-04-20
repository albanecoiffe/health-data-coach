from normalization.normalizer import normalize_metric
from normalization.time_resolver import (
    resolve_period,
    normalize_period_with_original_message,
)
from intents.intents import QueryResult
from core.metrics.metrics import METRIC_DEFINITION
from core.models.RunSession import RunSession
from sqlalchemy import func


def execute_get_metric(db, user_id, intent: dict):
    metric = normalize_metric(intent["metric"])

    if metric not in METRIC_DEFINITION:
        raise ValueError(f"Metric not supported: {metric}")

    spec = METRIC_DEFINITION[metric]

    period = normalize_period_with_original_message(
        intent["period"],
        intent.get("original_message", ""),
    )

    start, end = resolve_period(period)

    base_filter = (
        RunSession.user_id == user_id,
        RunSession.start_time >= start,
        RunSession.start_time < end,
    )

    col = spec["column"]
    agg = spec["aggregation"]

    if agg == "sum":
        expr = func.coalesce(func.sum(col), 0)
    elif agg == "avg":
        expr = func.coalesce(func.avg(col), 0)
    elif agg == "count":
        expr = func.count(col)
    else:
        raise ValueError(f"Unknown aggregation: {agg}")

    value = db.query(expr).filter(*base_filter).scalar()

    return QueryResult(
        metric=metric,
        aggregation=agg,
        start=start.isoformat(),
        end=end.isoformat(),
        value=value,
    )
