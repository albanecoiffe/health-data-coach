# coach/recommendation/schemas.py
from enum import Enum
from typing import List, TypedDict, Dict, Any


class WeekRecommendation(TypedDict):
    """
    Structured output of the recommendation engine (DB-native).
    """

    # --- Core targets
    target_sessions: int
    dominant_week_cluster: int
    avg_risk_last_3w: float
    risk_level: str  # "low" | "moderate" | "high"

    # --- Plans
    base_plan: List[str]
    adjusted_plan_remaining: List[str]
    remaining_sessions: List[str]

    # --- What has been done
    done_sessions: List[str]
    done_sessions_details: Any  # résumé structuré (engine-level)

    # --- State
    week_complete: bool

    # --- Context
    previous_week_had_sessions: bool
    previous_week_summary: Dict[str, float]


class SessionType(str, Enum):
    intensity = "intensity"
    easy = "easy"
    endurance = "endurance"
