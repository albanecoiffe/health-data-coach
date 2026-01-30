# ============================================================
# Recommendation Engine — Running Coach
# ============================================================
import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

from recommendation.loader import load_weeks, load_sessions
from recommendation.risk import compute_weekly_risk, risk_level_from_proba
from recommendation.clustering import (
    cluster_weeks,
    cluster_sessions,
)
from recommendation.schemas import WeekRecommendation

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

CUTOFF_DATE = "2025-09-14"

SESSION_LABELS = {
    0: "intensity",
    1: "easy",
    2: "endurance",
}

FEATURES_WEEK = [
    "distance_km",
    "sessions",
    "duration_min",
    "weekly_load",
    "high_intensity_pct",
]

FEATURES_SESSION = [
    "distance_km",
    "duration_min",
    "pace_min_per_km",
    "low_intensity_pct",
    "high_intensity_pct",
]

# ============================================================
# Session type explanations — Running Coach
# ============================================================

SESSION_PROFILES = {
    "easy": {
        "label": "Séance facile",
        "data_profile": {
            "avg_duration_min": 41,
            "avg_distance_km": 6.1,
            "low_intensity_pct": 0.93,
            "high_intensity_pct": 0.09,
        },
        "observed_range": {
            "distance_km": {"min": 2.5, "max": 8.1},
            "duration_min": {"min": 17, "max": 56},
        },
    },
    "endurance": {
        "label": "Séance d’endurance",
        "data_profile": {
            "avg_duration_min": 73,
            "avg_distance_km": 11.5,
            "low_intensity_pct": 0.89,
            "high_intensity_pct": 0.11,
        },
        "observed_range": {
            "distance_km": {"min": 8.4, "max": 15.3},
            "duration_min": {"min": 52, "max": 94},
        },
    },
    "intensity": {
        "label": "Séance intensive",
        "data_profile": {
            "avg_duration_min": 71,
            "avg_distance_km": 12.0,
            "low_intensity_pct": 0.46,
            "high_intensity_pct": 0.56,
        },
        "observed_range": {
            "distance_km": {"min": 7.0, "max": 21.3},
            "duration_min": {"min": 41, "max": 115},
        },
    },
}

SESSION_TEMPLATES = {
    # cluster_week -> ordered pattern
    0: ["intensity", "endurance", "easy", "easy", "easy"],
    1: ["intensity", "easy", "endurance", "easy"],
    2: ["easy", "endurance", "easy"],
}
# ------------------------------------------------------------
# INTERNAL HELPERS (unchanged)
# ------------------------------------------------------------


# recommendation/engine.py


def summarize_done_sessions(current_sessions: list[dict]) -> dict:
    """
    Summarize already completed sessions in the current week.
    DB-native version (list of dicts).
    """

    summary = {
        "count": 0,
        "types": {},
        "total_duration_min": 0.0,
        "total_distance_km": 0.0,
    }

    for s in current_sessions:
        summary["count"] += 1

        duration = float(s.get("duration_min") or 0.0)
        distance = float(s.get("distance_km") or 0.0)

        summary["total_duration_min"] += duration
        summary["total_distance_km"] += distance

        session_type = s.get("cluster_session")
        if session_type is not None:
            summary["types"][session_type] = summary["types"].get(session_type, 0) + 1

    summary["total_duration_min"] = round(summary["total_duration_min"], 1)
    summary["total_distance_km"] = round(summary["total_distance_km"], 1)

    return summary


def _compute_session_distribution(sessions, weeks):
    counts = (
        sessions.groupby(["week_start", "cluster_session"])
        .size()
        .reset_index(name="n_sessions")
    )

    counts = counts.merge(
        weeks[["week_start", "cluster_week"]],
        on="week_start",
        how="left",
    )

    dist = (
        counts.groupby(["cluster_week", "cluster_session"])["n_sessions"]
        .mean()
        .reset_index()
    )

    dist["pct"] = dist.groupby("cluster_week")["n_sessions"].transform(
        lambda x: x / x.sum()
    )

    return dist


def _compute_risk_scores(df):
    df = df.dropna(subset=FEATURES_WEEK).copy()
    load_threshold = df["weekly_load"].quantile(0.80)

    def is_risky(row):
        return int(
            row["cluster_week"] == 0
            or row["weekly_load"] > load_threshold
            or row["high_intensity_pct"] > 0.45
        )

    df["risk"] = df.apply(is_risky, axis=1)

    X = df[FEATURES_WEEK]
    y = df["risk"]

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", LogisticRegression()),
        ]
    )

    model.fit(X, y)
    df["risk_proba"] = model.predict_proba(X)[:, 1]

    return df


def _build_week_template(
    cluster_week: int, avg_sessions: int, dist_df=None
) -> list[str]:
    """
    DB-native week template builder.
    dist_df kept for backward compatibility but ignored.
    """
    # fallback safe
    pattern = SESSION_TEMPLATES.get(int(cluster_week), ["easy", "endurance", "easy"])

    plan = []
    i = 0
    while len(plan) < avg_sessions:
        plan.append(pattern[i % len(pattern)])
        i += 1

    return plan[:avg_sessions]


def _adjust_plan_by_risk(plan, avg_risk):
    if avg_risk > 0.75:
        return ["easy" if s == "intensity" else s for s in plan]
    if avg_risk < 0.30 and "intensity" not in plan:
        plan[-1] = "intensity"
    return plan


def _adjust_with_done_sessions(
    base_plan: list[str],
    done_types: list[str],
    remaining_sessions_count: int,
) -> list[str]:
    """
    Remove already completed session types from the base plan when possible,
    then keep only the number of remaining sessions.
    """
    plan_copy = base_plan.copy()

    # Remove done sessions if present in plan
    for done in done_types:
        if done in plan_copy:
            plan_copy.remove(done)

    adjusted = plan_copy[:remaining_sessions_count]

    # pad with easy if needed
    while len(adjusted) < remaining_sessions_count:
        adjusted.append("easy")

    return adjusted


def enrich_plan_with_descriptions(plan: list[str]) -> list[dict]:
    """
    Convert a list of session types into rich session recommendations.
    """
    enriched = []

    for session_type in plan:
        profile = SESSION_PROFILES.get(session_type)

        if profile is None:
            continue

        enriched.append(
            {
                "type": session_type,
                "label": profile["label"],
                "data_profile": profile["data_profile"],
                "observed_range": profile.get("observed_range"),
            }
        )

    return enriched
