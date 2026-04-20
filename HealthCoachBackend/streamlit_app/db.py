import os
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def resolve_user_id() -> str:
    user_id = os.getenv("USER_ID") or os.getenv("DEFAULT_USER_ID")
    if not user_id:
        raise RuntimeError("USER_ID or DEFAULT_USER_ID missing")
    return user_id


def load_sessions_between(user_id: str, start_date: date, end_date: date) -> pd.DataFrame:
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
          AND start_time >= :start_date
          AND start_time < :end_date
        ORDER BY start_time ASC
        """
    )

    with engine.connect() as conn:
        df = pd.read_sql(
            query,
            conn,
            params={
                "user_id": user_id,
                "start_date": pd.Timestamp(start_date),
                "end_date": pd.Timestamp(end_date),
            },
        )

    if df.empty:
        return df

    df["start_time"] = pd.to_datetime(df["start_time"])
    for col in [
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
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    duration_safe = df["duration_min"].replace(0, pd.NA)
    distance_safe = df["distance_km"].replace(0, pd.NA)
    df["pace_min_per_km"] = duration_safe / distance_safe

    z_low = df["z1_min"] + df["z2_min"] + df["z3_min"]
    z_high = df["z4_min"] + df["z5_min"]
    z_total = z_low + z_high
    z_total_safe = z_total.replace(0, pd.NA)
    df["low_intensity_pct"] = (z_low / z_total_safe).fillna(0.0)
    df["high_intensity_pct"] = (z_high / z_total_safe).fillna(0.0)

    return df


def load_all_sessions(user_id: str) -> pd.DataFrame:
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

    if df.empty:
        return df

    df["start_time"] = pd.to_datetime(df["start_time"])
    for col in [
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
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return df
