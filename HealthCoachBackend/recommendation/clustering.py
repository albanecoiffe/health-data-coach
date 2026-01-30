# ============================================================
# Clustering logic — Running Coach
# ============================================================

import pandas as pd
import joblib
import numpy as np
from typing import List, Dict

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

FEATURES_WEEK = [
    "distance_km",
    "sessions",
    "duration_min",
    "weekly_load",
    "low_intensity_pct",
    "high_intensity_pct",
]


FEATURES_SESSION = [
    "distance_km",
    "duration_min",
    "pace_min_per_km",
    "low_intensity_pct",
    "high_intensity_pct",
]

# ------------------------------------------------------------
# Modeles
# ------------------------------------------------------------
scaler_sessions = joblib.load("recommendation/models/scaler_session.joblib")
kmeans_sessions = joblib.load("recommendation/models/kmeans3_session.joblib")

scaler_week = joblib.load("recommendation/models/scaler_week.joblib")
kmeans_week = joblib.load("recommendation/models/kmeans3_week.joblib")
# ------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------


# ------------------------------------------------------------
# WEEK CLUSTERING
# ------------------------------------------------------------
def cluster_weeks(run_weeks) -> int | None:
    """
    Return dominant week cluster over provided RunWeek objects.
    """
    if not run_weeks:
        return None

    feature_names = list(scaler_week.feature_names_in_)

    rows = []
    for w in run_weeks:
        rows.append(
            {
                "distance_km": float(w.total_distance_km or 0.0),
                "sessions": int(w.sessions_count or 0),
                "duration_min": float(w.total_duration_min or 0.0),
                "weekly_load": float(w.avg_load or 0.0),
                "low_intensity_pct": float(w.z1_z3_pct or 0.0),
                "high_intensity_pct": float(w.z4_z5_pct or 0.0),
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        return None

    # 🔒 strict ML alignment
    X = df[feature_names]

    X_scaled = scaler_week.transform(X)
    labels = kmeans_week.predict(X_scaled)

    return int(np.bincount(labels).argmax())


# ------------------------------------------------------------
# SESSION CLUSTERING
# ------------------------------------------------------------
def cluster_sessions(run_sessions: List[Dict]) -> List[Dict]:
    """
    Cluster running sessions from DB-native dicts.
    Returns same dicts enriched with `cluster_session`.
    Only sessions with full ML feature set are clustered.
    """

    if not run_sessions:
        return []

    feature_names = list(scaler_sessions.feature_names_in_)

    rows = []
    valid_sessions = []

    for s in run_sessions:
        # Durée obligatoire
        duration = s.get("duration_min")
        if duration is None or duration <= 0:
            continue

        row = {
            "distance_km": s.get("distance_km"),
            "duration_min": duration,
            "pace_min_per_km": s.get("pace_min_per_km"),
            "low_intensity_pct": s.get("low_intensity_pct"),
            "high_intensity_pct": s.get("high_intensity_pct"),
        }

        # 🔒 exclusion stricte si feature manquante
        if any(row[f] is None for f in feature_names):
            continue

        rows.append(row)
        valid_sessions.append(s)

    if not rows:
        return []

    df = pd.DataFrame(rows)

    # 🔒 strict ML alignment
    X = df[feature_names]

    X_scaled = scaler_sessions.transform(X)
    labels = kmeans_sessions.predict(X_scaled)

    for s, label in zip(valid_sessions, labels):
        s["cluster_session"] = int(label)

    return valid_sessions
