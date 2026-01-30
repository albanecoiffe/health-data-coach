# semantic layer: metrics/aggregations autorisées

# intent_based_querying/registry.py
from sqlalchemy import func
from models.RunSession import RunSession

# --------------------------------------------------
# Metrics registry (source of truth)
# --------------------------------------------------

METRICS = {
    "DISTANCE": {
        "column": RunSession.distance_km,
        "aggregation": func.sum,
        "label": "km",
    },
    "DURATION": {
        "column": RunSession.duration_min,
        "aggregation": func.sum,
        "label": "minutes",
    },
    "SESSIONS": {
        "column": RunSession.id,
        "aggregation": func.count,
        "label": "séances",
    },
    "ELEVATION": {
        "column": RunSession.elevation_m,
        "aggregation": func.sum,
        "label": "m",
    },
    "AVG_HR": {
        "column": RunSession.avg_hr,
        "aggregation": func.avg,
        "label": "bpm",
    },
    "ACTIVE_KCAL": {
        "column": RunSession.active_kcal,
        "aggregation": func.sum,
        "label": "kcal",
    },
}
