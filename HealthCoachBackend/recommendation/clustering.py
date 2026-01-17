# ============================================================
# Clustering logic — Running Coach
# ============================================================

import pandas as pd
import joblib

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
scaler_sessions = joblib.load("models/scaler_session.joblib")
kmeans_sessions = joblib.load("models/kmeans3_session.joblib")

scaler_week = joblib.load("models/scaler_week.joblib")
kmeans_week = joblib.load("models/kmeans3_week.joblib")

# ------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------


def cluster_weeks(
    weeks_df: pd.DataFrame,
    n_clusters: int = 3,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Cluster training weeks into profiles (e.g. controlled, intensive, short).

    Parameters
    ----------
    weeks_df : pd.DataFrame
        Weekly aggregated training data.
    n_clusters : int
        Number of clusters (default = 3).
    random_state : int
        Random state for reproducibility.

    Returns
    -------
    pd.DataFrame
        weeks_df enriched with 'cluster_week'.
    """

    df = weeks_df.dropna(subset=FEATURES_WEEK).copy()

    X = df[scaler_week.feature_names_in_]
    X_scaled = scaler_week.transform(X)

    df["cluster_week"] = kmeans_week.predict(X_scaled)

    return df


def cluster_sessions(
    sessions_df: pd.DataFrame,
    n_clusters: int = 3,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Cluster individual running sessions into session types.

    Parameters
    ----------
    sessions_df : pd.DataFrame
        Individual running sessions.
    n_clusters : int
        Number of clusters (default = 3).
    random_state : int
        Random state for reproducibility.

    Returns
    -------
    pd.DataFrame
        sessions_df enriched with 'cluster_session'.
    """

    df = sessions_df.dropna(subset=FEATURES_SESSION).copy()

    X = df[scaler_sessions.feature_names_in_]
    X_scaled = scaler_sessions.transform(X)

    df["cluster_session"] = kmeans_sessions.predict(X_scaled)

    return df
