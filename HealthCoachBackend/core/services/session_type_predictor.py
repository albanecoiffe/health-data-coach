from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from core.heart_rate_zones import high_intensity_minutes, low_intensity_minutes
from core.models.RunSession import RunSession


FEATURE_COLUMNS = [
    "distance_km",
    "duration_min",
    "pace_min_per_km",
    "avg_hr",
    "elevation_m",
    "active_kcal",
    "z1_min",
    "z2_min",
    "z3_min",
    "z4_min",
    "z5_min",
    "low_intensity_pct",
    "high_intensity_pct",
]

SUPPORTED_SESSION_TYPES = {
    "footing",
    "fractionné",
    "sortie longue",
    "semi marathon",
    "marathon",
}


def _build_feature_row(session: RunSession) -> dict[str, float | None]:
    distance = float(session.distance_km) if session.distance_km else 0.0
    duration = float(session.duration_min) if session.duration_min else 0.0
    pace = duration / distance if distance > 0 and duration > 0 else None
    low_pct = low_intensity_minutes(session) / duration if duration > 0 else 0.0
    high_pct = high_intensity_minutes(session) / duration if duration > 0 else 0.0

    return {
        "distance_km": distance if distance > 0 else None,
        "duration_min": duration if duration > 0 else None,
        "pace_min_per_km": pace,
        "avg_hr": float(session.avg_hr) if session.avg_hr is not None else None,
        "elevation_m": float(session.elevation_m) if session.elevation_m is not None else None,
        "active_kcal": float(session.active_kcal) if session.active_kcal is not None else None,
        "z1_min": float(session.z1_min) if session.z1_min is not None else 0.0,
        "z2_min": float(session.z2_min) if session.z2_min is not None else 0.0,
        "z3_min": float(session.z3_min) if session.z3_min is not None else 0.0,
        "z4_min": float(session.z4_min) if session.z4_min is not None else 0.0,
        "z5_min": float(session.z5_min) if session.z5_min is not None else 0.0,
        "low_intensity_pct": low_pct,
        "high_intensity_pct": high_pct,
    }


def _fallback_prediction(session: RunSession) -> str:
    row = _build_feature_row(session)
    distance = float(row["distance_km"] or 0.0)
    duration = float(row["duration_min"] or 0.0)
    high_pct = float(row["high_intensity_pct"] or 0.0)
    avg_hr = float(row["avg_hr"] or 0.0)

    if distance >= 18 or duration >= 100:
        return "sortie longue"
    if high_pct >= 0.18 or avg_hr >= 165:
        return "fractionné"
    return "footing"


def predict_session_type(
    db: Session,
    user_id,
    target_session: RunSession,
) -> str | None:
    predictor = build_session_type_predictor(db, user_id)
    return predictor(target_session)


def build_session_type_predictor(
    db: Session,
    user_id,
) -> Callable[[RunSession], str | None]:
    labeled_sessions = (
        db.query(RunSession)
        .filter(
            RunSession.user_id == user_id,
            RunSession.session_type.isnot(None),
            RunSession.merged_into_start_time.is_(None),
        )
        .all()
    )

    training_rows: list[dict[str, Any]] = []
    training_labels: list[str] = []

    for session in labeled_sessions:
        label = (session.session_type or "").strip()
        if not label or label not in SUPPORTED_SESSION_TYPES:
            continue
        training_rows.append(_build_feature_row(session))
        training_labels.append(label)

    label_counts = Counter(training_labels)
    eligible_labels = {label for label, count in label_counts.items() if count >= 3}

    if len(eligible_labels) < 2:
        return _fallback_prediction

    filtered_rows = [
        row for row, label in zip(training_rows, training_labels) if label in eligible_labels
    ]
    filtered_labels = [
        label for label in training_labels if label in eligible_labels
    ]

    if len(set(filtered_labels)) < 2:
        return _fallback_prediction

    classifier = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=2000)),
        ]
    )

    X_train = pd.DataFrame(filtered_rows, columns=FEATURE_COLUMNS)
    y_train = pd.Series(filtered_labels)

    try:
        classifier.fit(X_train, y_train)

        def _predict(target_session: RunSession) -> str | None:
            if target_session.session_type and target_session.session_type.strip():
                return target_session.session_type.strip()

            X_target = pd.DataFrame([_build_feature_row(target_session)], columns=FEATURE_COLUMNS)
            try:
                prediction = classifier.predict(X_target)[0]
                return str(prediction)
            except Exception:
                return _fallback_prediction(target_session)

        return _predict
    except Exception:
        return _fallback_prediction
