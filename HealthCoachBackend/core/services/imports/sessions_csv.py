import os
import threading
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from sqlalchemy.exc import IntegrityError

from core.models.RunSession import RunSession
from core.services.run_weeks.builder import build_run_weeks
from core.services.signature.signature_store import invalidate_signature
from database import SessionLocal


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SESSIONS_CSV_PATH = PROJECT_ROOT / "exploration" / "sessions_received.csv"


def resolve_sessions_csv_path(csv_path: str | None = None) -> Path:
    if csv_path:
        return Path(csv_path).expanduser()

    env_path = os.getenv("SESSIONS_CSV_PATH")
    if env_path:
        return Path(env_path).expanduser()

    return DEFAULT_SESSIONS_CSV_PATH


def _to_float(value: Any, default: float | None = None) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_value(row: pd.Series, *keys: str) -> Any:
    for key in keys:
        if key in row and not pd.isna(row[key]):
            return row[key]
    return None


def _prepare_start_time_column(df: pd.DataFrame) -> pd.DataFrame:
    if "start_time" in df.columns:
        return df

    if "date" not in df.columns:
        return df

    out = df.copy()
    parsed = pd.to_datetime(out["date"], errors="coerce")
    rank = parsed.groupby(parsed.dt.date).cumcount()
    out["_computed_start_time"] = parsed.dt.normalize() + pd.to_timedelta(
        12 * 60 + rank, unit="m"
    )
    return out


def _parse_start_time(row: pd.Series):
    raw = _get_value(row, "start_time", "_computed_start_time", "date")
    ts = pd.to_datetime(raw, errors="coerce")
    if pd.isna(ts):
        raise ValueError("invalid start_time/date")
    return ts.to_pydatetime()


def _resolve_user_id(explicit_user_id: str | None) -> UUID:
    value = explicit_user_id or os.getenv("DEFAULT_USER_ID")
    if not value:
        raise ValueError("Missing user_id and DEFAULT_USER_ID")
    return UUID(str(value))


def import_sessions_dataframe(df: pd.DataFrame, user_id: str | None = None) -> dict[str, Any]:
    df = _prepare_start_time_column(df)
    resolved_user_id = _resolve_user_id(user_id)

    stats = {
        "status": "ok",
        "total_rows": int(len(df)),
        "inserted": 0,
        "duplicates": 0,
        "invalid_rows": 0,
        "errors": [],
        "user_id": str(resolved_user_id),
    }

    db = SessionLocal()
    try:
        for idx, row in df.iterrows():
            try:
                session = RunSession(
                    user_id=resolved_user_id,
                    start_time=_parse_start_time(row),
                    distance_km=_to_float(_get_value(row, "distance_km"), 0.0),
                    duration_min=_to_float(_get_value(row, "duration_min"), 0.0),
                    avg_hr=_to_float(_get_value(row, "avg_hr")),
                    z1_min=_to_float(_get_value(row, "z1_min", "z1"), 0.0),
                    z2_min=_to_float(_get_value(row, "z2_min", "z2"), 0.0),
                    z3_min=_to_float(_get_value(row, "z3_min", "z3"), 0.0),
                    z4_min=_to_float(_get_value(row, "z4_min", "z4"), 0.0),
                    z5_min=_to_float(_get_value(row, "z5_min", "z5"), 0.0),
                    elevation_m=_to_float(_get_value(row, "elevation_m")),
                    active_kcal=_to_float(_get_value(row, "active_kcal")),
                )
                db.add(session)
                db.commit()
                stats["inserted"] += 1

            except IntegrityError:
                db.rollback()
                stats["duplicates"] += 1
            except Exception as exc:
                db.rollback()
                stats["invalid_rows"] += 1
                if len(stats["errors"]) < 10:
                    stats["errors"].append(f"row {idx}: {exc}")

        if stats["inserted"] > 0:
            build_run_weeks(db, resolved_user_id)
            invalidate_signature(db, resolved_user_id)

        return stats
    finally:
        db.close()


def import_sessions_csv_file(
    csv_path: str | None = None, user_id: str | None = None
) -> dict[str, Any]:
    path = resolve_sessions_csv_path(csv_path)
    if not path.exists():
        return {
            "status": "missing_file",
            "path": str(path),
            "inserted": 0,
            "duplicates": 0,
            "invalid_rows": 0,
        }

    df = pd.read_csv(path)
    stats = import_sessions_dataframe(df, user_id=user_id)
    stats["path"] = str(path)
    return stats


def auto_import_sessions_on_startup() -> dict[str, Any]:
    enabled = os.getenv("AUTO_IMPORT_SESSIONS_ON_STARTUP", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if not enabled:
        return {"status": "disabled"}

    return import_sessions_csv_file()


def _signature(path: Path) -> tuple[int, int] | None:
    if not path.exists():
        return None
    stat = path.stat()
    return (stat.st_mtime_ns, stat.st_size)


def _csv_poller_loop(interval_s: int):
    last_seen_sig: tuple[int, int] | None = None
    while True:
        try:
            path = resolve_sessions_csv_path()
            current_sig = _signature(path)
            if current_sig is not None and current_sig != last_seen_sig:
                result = import_sessions_csv_file()
                print("🔁 CSV poll import:", result)
                last_seen_sig = current_sig
        except Exception as exc:
            print("⚠️ CSV poll import error:", exc)
        time.sleep(interval_s)


def start_csv_polling_worker() -> dict[str, Any]:
    interval_s = int(os.getenv("SESSIONS_CSV_POLL_SECONDS", "0"))
    if interval_s <= 0:
        return {"status": "disabled", "reason": "SESSIONS_CSV_POLL_SECONDS<=0"}

    thread = threading.Thread(
        target=_csv_poller_loop,
        args=(interval_s,),
        daemon=True,
        name="sessions-csv-poller",
    )
    thread.start()
    return {"status": "started", "interval_seconds": interval_s}
