from sqlalchemy import func
from models.RunSession import RunSession

from normalization.normalizer import normalize_metric
from normalization.time_resolver import (
    resolve_period,
    normalize_period_with_original_message,
)
from intents.intents import QueryResult


def execute_get_metric(db, user_id, intent: dict):
    print("\n⚙️ EXECUTOR: GET_METRIC")

    metric = normalize_metric(intent["metric"])

    # 🔹 NOUVEAU : normalisation défensive de la période
    raw_period = intent["period"]
    original_message = intent.get("original_message", "")

    period = normalize_period_with_original_message(raw_period, original_message)

    # 🔹 resolve_period accepte str OU dict (named_month)
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
        aggregation="sum",
        start=start.isoformat(),
        end=end.isoformat(),
        value=value,
    )
