# DSL + schémas Pydantic (Intent JSON)

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional, Union, Dict, Any

# -----------------------
# Périodes autorisées
# -----------------------
RelativePeriod = Literal[
    "today",
    "yesterday",
    "this_week",
    "last_week",
    "this_month",
    "last_month",
    "this_year",
    "last_year",
    "last_7_days",
    "last_28_days",
]

Aggregation = Literal["sum", "avg", "max", "min", "count"]

Metric = Literal[
    "distance_km",
    "duration_min",
    "sessions",
    "avg_hr",
    "elevation_m",
    "active_kcal",
]


# -----------------------
# Intent 1 : GET_METRIC
# -----------------------
class GetMetricIntent(BaseModel):
    intent: Literal["GET_METRIC"]
    metric: Metric
    aggregation: Aggregation
    period: RelativePeriod


# -----------------------
# Intent 2 : COMPARE_PERIODS
# -----------------------
class ComparePeriodsIntent(BaseModel):
    intent: Literal["COMPARE_PERIODS"]
    metric: Metric
    aggregation: Aggregation
    left_period: RelativePeriod
    right_period: RelativePeriod


class CompareResult(BaseModel):
    metric: str
    aggregation: str
    left_period: RelativePeriod
    right_period: RelativePeriod
    left_value: float | int | None
    right_value: float | int | None


# -----------------------
# Intent 3 : Bilan / Summary
# -----------------------
class PeriodSummaryIntent(BaseModel):
    intent: Literal["PERIOD_SUMMARY"]
    period: RelativePeriod


class PeriodSummaryResult(BaseModel):
    period: str
    sessions: int
    distance_km: float
    duration_min: float
    avg_hr: Optional[float]
    elevation_m: float
    active_kcal: float


# -----------------------
# Intent 4 : SMALL TALK
# -----------------------
class SmallTalkIntent(BaseModel):
    intent: Literal["SMALL_TALK"]


# -----------------------
# Intent 5 : COACHING
# -----------------------
class CoachingIntent(BaseModel):
    intent: Literal["COACHING"]


class CoachingResult(BaseModel):
    coaching_type: Optional[str] = None
    signature: Optional[Dict[str, Any]] = None
    facts: Optional[Dict[str, Any]] = None

    error: Optional[str] = None
    message: Optional[str] = None


# -----------------------
# Intent 6 : RECOMMENDATION
# -----------------------
class RecommendationIntent(BaseModel):
    intent: Literal["RECOMMENDATION"]
    recommendation_type: Optional[str] = None


# -----------------------
# Union global (ce que le LLM peut produire)
# -----------------------
Intent = Union[
    GetMetricIntent,
    ComparePeriodsIntent,
    PeriodSummaryIntent,
    SmallTalkIntent,
    CoachingIntent,
]


# -----------------------
# Résultat normalisé de l'exécution
# -----------------------
class QueryResult(BaseModel):
    metric: str
    aggregation: str
    start: str
    end: str
    value: float | int | None
