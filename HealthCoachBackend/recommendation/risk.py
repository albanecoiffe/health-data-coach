# ============================================================
# Risk estimation — Running Coach
# ============================================================

import pandas as pd
from sklearn.pipeline import Pipeline
import pandas as pd
import joblib

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

FEATURES_RISK = [
    "distance_km",
    "sessions",
    "duration_min",
    "weekly_load",
    "high_intensity_pct",
]

risk_pipeline = joblib.load("models/risk_pipeline.joblib")


# ------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------


def compute_weekly_risk(weeks_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute a probabilistic overload risk score for each week.

    This score is a short-term training load indicator,
    NOT a medical or injury prediction.
    """

    df = weeks_df.dropna(subset=FEATURES_RISK).copy()

    # Predict probability of risk
    df["risk_proba"] = risk_pipeline.predict_proba(df[FEATURES_RISK])[:, 1]

    return df


def risk_level_from_proba(risk_proba: float) -> str:
    """
    Convert a risk probability into a readable risk level.
    """

    if risk_proba > 0.75:
        return "high"
    if risk_proba > 0.40:
        return "moderate"
    return "low"


# ------------------------------------------------------------
# OPTIONAL UTILITIES
# ------------------------------------------------------------


def risk_level_from_proba(risk_proba: float) -> str:
    """
    Convert a risk probability into a readable risk level.

    Parameters
    ----------
    risk_proba : float

    Returns
    -------
    str
        "low", "moderate", or "high"
    """

    if risk_proba > 0.75:
        return "high"
    if risk_proba > 0.40:
        return "moderate"
    return "low"
