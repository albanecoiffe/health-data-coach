# coach/recommendation/schemas.py
from enum import Enum
from typing import List, TypedDict


class WeekRecommendation(TypedDict):
    """
    Structured output of the recommendation engine.
    """

    target_sessions: int
    dominant_week_cluster: int
    avg_risk_last_3w: float
    risk_level: str
    base_plan: List[str]
    adjusted_plan_remaining: List[str]
    done_sessions: List[str]


class SessionType(str, Enum):
    intensity = "intensity"
    easy = "easy"
    endurance = "endurance"
