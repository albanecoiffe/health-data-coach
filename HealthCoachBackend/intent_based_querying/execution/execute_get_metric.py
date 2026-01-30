from sqlalchemy import func
from models.RunSession import RunSession

from intent_based_querying.normalization.normalizer import normalize_metric
from intent_based_querying.normalization.time_resolver import resolve_period
from intent_based_querying.intents.intents import QueryResult


def execute_get_metric(db, user_id, intent: dict):
    print("\n⚙️ EXECUTOR: GET_METRIC")

    metric = normalize_metric(intent["metric"])
    period = intent["period"]
    if not isinstance(period, str):
        raise TypeError(f"period must be str, got {type(period)}: {period}")

    start, end = resolve_period(period)

    base_filter = (
        RunSession.user_id == user_id,
        RunSession.start_time >= start,
        RunSession.start_time < end,
    )

    if metric == "distance_km":
        value = (
            db.query(func.coalesce(func.sum(RunSession.distance_km), 0))
            .filter(*base_filter)
            .scalar()
        )

    elif metric == "sessions":
        value = db.query(func.count(RunSession.id)).filter(*base_filter).scalar()

    elif metric == "duration_min":
        value = (
            db.query(func.coalesce(func.sum(RunSession.duration_min), 0))
            .filter(*base_filter)
            .scalar()
        )

    elif metric == "avg_hr":
        value = (
            db.query(func.coalesce(func.avg(RunSession.avg_hr), 0))
            .filter(*base_filter)
            .scalar()
        )

    elif metric == "elevation_m":
        value = (
            db.query(func.coalesce(func.sum(RunSession.elevation_m), 0))
            .filter(*base_filter)
            .scalar()
        )

    elif metric == "active_kcal":
        value = (
            db.query(func.coalesce(func.sum(RunSession.active_kcal), 0))
            .filter(*base_filter)
            .scalar()
        )

    else:
        raise ValueError(f"Metric not supported: {metric}")

    print(f"✅ Computed value for {metric} from {start} to {end} : {value}")

    return QueryResult(
        metric=metric,
        aggregation="sum",  # ou "count" selon metric si tu veux affiner plus tard
        start=start.isoformat(),
        end=end.isoformat(),
        value=value,
    )
