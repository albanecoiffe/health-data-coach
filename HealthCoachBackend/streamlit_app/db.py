import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.heart_rate_zones import (
    HIGH_INTENSITY_ZONE_IDS,
    LOW_INTENSITY_ZONE_IDS,
    zone_columns,
)
from core.models.RunSession import RunSession
from core.services.session_type_predictor import predict_session_type
from core.services.signature.signature_store import invalidate_signature

load_dotenv(_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
engine = (
    create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    if DATABASE_URL
    else None
)
SessionLocal = sessionmaker(bind=engine) if engine else None


def resolve_user_id() -> str | None:
    return os.getenv("USER_ID") or os.getenv("DEFAULT_USER_ID")


def _normalize_sessions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    if "start_time" not in df.columns and "date" in df.columns:
        df = df.rename(columns={"date": "start_time"})

    df["start_time"] = pd.to_datetime(df["start_time"])

    if "session_type" not in df.columns:
        df["session_type"] = None
    if "predicted_session_type" not in df.columns:
        df["predicted_session_type"] = None
    if "session_detail" not in df.columns:
        df["session_detail"] = None

    df["session_type"] = df["session_type"].where(df["session_type"].notna(), None)
    df["predicted_session_type"] = df["predicted_session_type"].where(
        df["predicted_session_type"].notna(), None
    )
    df["session_detail"] = df["session_detail"].where(df["session_detail"].notna(), None)
    df["effective_session_type"] = df["session_type"].combine_first(
        df["predicted_session_type"]
    )

    numeric_cols = (
        "distance_km",
        "duration_min",
        "avg_hr",
        "elevation_m",
        "active_kcal",
        *zone_columns(),
    )
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    duration_safe = df["duration_min"].replace(0, pd.NA)
    distance_safe = df["distance_km"].replace(0, pd.NA)
    df["pace_min_per_km"] = (duration_safe / distance_safe).fillna(0.0)

    z_low = df[zone_columns(LOW_INTENSITY_ZONE_IDS)].sum(axis=1)
    z_high = df[zone_columns(HIGH_INTENSITY_ZONE_IDS)].sum(axis=1)
    z_total_safe = (z_low + z_high).replace(0, pd.NA)
    df["low_intensity_pct"] = (z_low / z_total_safe).fillna(0.0)
    df["high_intensity_pct"] = (z_high / z_total_safe).fillna(0.0)

    return df.sort_values("start_time")


def _load_csv_sessions() -> pd.DataFrame:
    csv_path = _ROOT / "sessions_received.csv"
    if not csv_path.exists():
        return pd.DataFrame()
    return _normalize_sessions(pd.read_csv(csv_path))


def _read_sql_with_reconnect(query, params: dict[str, object]) -> pd.DataFrame:
    if not engine:
        return pd.DataFrame()

    try:
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params=params)
    except OperationalError:
        engine.dispose()
        with engine.connect() as conn:
            return pd.read_sql(query, conn, params=params)


def load_all_sessions(user_id: str | None = None) -> pd.DataFrame:
    if not engine or not user_id:
        return _load_csv_sessions()

    if not SessionLocal:
        return _load_csv_sessions()

    db = SessionLocal()
    try:
        sessions = (
            db.query(RunSession)
            .filter(RunSession.user_id == user_id)
            .order_by(RunSession.start_time.asc())
            .all()
        )

        rows = []
        for session in sessions:
            predicted = None
            if not session.session_type:
                predicted = predict_session_type(db, session.user_id, session)

            rows.append(
                {
                    "start_time": session.start_time,
                    "distance_km": session.distance_km,
                    "duration_min": session.duration_min,
                    "avg_hr": session.avg_hr,
                    "elevation_m": session.elevation_m,
                    "active_kcal": session.active_kcal,
                    "z1_min": session.z1_min,
                    "z2_min": session.z2_min,
                    "z3_min": session.z3_min,
                    "z4_min": session.z4_min,
                    "z5_min": session.z5_min,
                    "session_type": session.session_type,
                    "predicted_session_type": predicted,
                    "session_detail": session.session_detail,
                }
            )

        df = pd.DataFrame(rows)
    finally:
        db.close()

    return _normalize_sessions(df)


def load_sessions_between(
    user_id: str | None,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    df = load_all_sessions(user_id)
    if df.empty:
        return df
    mask = (df["start_time"] >= pd.Timestamp(start_date)) & (
        df["start_time"] < pd.Timestamp(end_date)
    )
    return df.loc[mask].copy()


def update_session_metadata(
    user_id: str,
    start_time,
    session_type: str | None,
    session_detail: str | None,
) -> None:
    if not SessionLocal:
        raise RuntimeError("Database unavailable")

    db = SessionLocal()
    try:
        session = (
            db.query(RunSession)
            .filter(
                RunSession.user_id == user_id,
                RunSession.start_time == pd.Timestamp(start_time).to_pydatetime(),
            )
            .first()
        )

        if not session:
            raise RuntimeError("Session introuvable")

        session.session_type = session_type.strip() if session_type and session_type.strip() else None
        session.session_detail = (
            session_detail.strip() if session_detail and session_detail.strip() else None
        )
        db.commit()
        invalidate_signature(db, user_id)
    finally:
        db.close()
