import os
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL) if DATABASE_URL else None


def resolve_user_id() -> str | None:
    return os.getenv("USER_ID") or os.getenv("DEFAULT_USER_ID")


def _normalize_sessions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    if "start_time" not in df.columns and "date" in df.columns:
        df = df.rename(columns={"date": "start_time"})

    df["start_time"] = pd.to_datetime(df["start_time"])

    numeric_cols = (
        "distance_km",
        "duration_min",
        "avg_hr",
        "elevation_m",
        "active_kcal",
        "z1_min",
        "z2_min",
        "z3_min",
        "z4_min",
        "z5_min",
    )
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    duration_safe = df["duration_min"].replace(0, pd.NA)
    distance_safe = df["distance_km"].replace(0, pd.NA)
    df["pace_min_per_km"] = (duration_safe / distance_safe).fillna(0.0)

    z_low = df["z1_min"] + df["z2_min"] + df["z3_min"]
    z_high = df["z4_min"] + df["z5_min"]
    z_total_safe = (z_low + z_high).replace(0, pd.NA)
    df["low_intensity_pct"] = (z_low / z_total_safe).fillna(0.0)
    df["high_intensity_pct"] = (z_high / z_total_safe).fillna(0.0)

    return df.sort_values("start_time")


def _load_csv_sessions() -> pd.DataFrame:
    csv_path = _ROOT / "sessions_received.csv"
    if not csv_path.exists():
        return pd.DataFrame()
    return _normalize_sessions(pd.read_csv(csv_path))


def load_all_sessions(user_id: str | None = None) -> pd.DataFrame:
    if not engine or not user_id:
        return _load_csv_sessions()

    query = text(
        """
        SELECT
            start_time,
            distance_km,
            duration_min,
            avg_hr,
            elevation_m,
            active_kcal,
            z1_min,
            z2_min,
            z3_min,
            z4_min,
            z5_min
        FROM run_sessions
        WHERE user_id = CAST(:user_id AS uuid)
        ORDER BY start_time ASC
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"user_id": user_id})
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
