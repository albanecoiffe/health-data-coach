from sqlalchemy import func
from core.models.RunSession import RunSession

METRIC_DEFINITION = {
    "distance_km": {
        "column": RunSession.distance_km,
        "aggregation": "sum",
    },
    "duration_min": {
        "column": RunSession.duration_min,
        "aggregation": "sum",
    },
    "avg_hr": {
        "column": RunSession.avg_hr,
        "aggregation": "avg",
    },
    "elevation_m": {
        "column": RunSession.elevation_m,
        "aggregation": "sum",
    },
    "active_kcal": {
        "column": RunSession.active_kcal,
        "aggregation": "sum",
    },
    "z1_min": {"column": RunSession.z1_min, "aggregation": "sum"},
    "z2_min": {"column": RunSession.z2_min, "aggregation": "sum"},
    "z3_min": {"column": RunSession.z3_min, "aggregation": "sum"},
    "z4_min": {"column": RunSession.z4_min, "aggregation": "sum"},
    "z5_min": {"column": RunSession.z5_min, "aggregation": "sum"},
    "sessions": {
        "column": RunSession.id,
        "aggregation": "count",
    },
}
