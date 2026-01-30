# ============================================================
# Risk estimation — Running Coach
# ============================================================

import pandas as pd
from sklearn.pipeline import Pipeline
import pandas as pd
import joblib
import numpy as np

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

risk_pipeline = joblib.load("recommendation/models/risk_pipeline.joblib")


# ------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------


def compute_weekly_risk(run_weeks) -> float:
    """
    Retourne un score moyen de risque sur les semaines fournies
    """
    if not run_weeks:
        return 0.0

    # 🔒 vérité ML
    scaler = risk_pipeline.named_steps["scaler"]
    feature_names = list(scaler.feature_names_in_)

    df = pd.DataFrame(
        [
            {
                "distance_km": w.total_distance_km,
                "sessions": w.sessions_count,
                "duration_min": w.total_duration_min,
                "weekly_load": w.avg_load,
                "high_intensity_pct": w.z4_z5_pct,
            }
            for w in run_weeks
        ]
    )

    # 🔥 alignement STRICT
    X = df[feature_names]

    risk_probas = risk_pipeline.predict_proba(X)[:, 1]

    return float(risk_probas.mean())


def risk_level_from_proba(risk_proba: float) -> str:
    """
    Convert a risk probability into a readable risk level.
    """

    if risk_proba > 0.75:
        return "high"
    if risk_proba > 0.40:
        return "moderate"
    return "low"
