import json
import re
from io import BytesIO
from typing import Any

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from core.config import get_settings
from core.services.imports.sessions_csv import import_sessions_dataframe


router = APIRouter(prefix="/api")


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _pick(record: dict[str, Any], *aliases: str) -> Any:
    normalized = {_normalize_key(k): v for k, v in record.items()}
    for alias in aliases:
        value = normalized.get(_normalize_key(alias))
        if value is not None:
            return value
    return None


def _as_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", ".")
        m = re.search(r"-?\d+(\.\d+)?", cleaned)
        if m:
            return float(m.group(0))
    return default


def _distance_km(record: dict[str, Any]) -> float:
    km = _as_float(
        _pick(
            record,
            "distance_km",
            "distanceKm",
            "distanceInKm",
            "totalDistanceKm",
        )
    )
    if km is not None:
        return km

    meters = _as_float(
        _pick(
            record,
            "distance_m",
            "distanceMeters",
            "distance",
            "totalDistance",
        )
    )
    if meters is None:
        return 0.0

    # Most Health exports use meters for raw distance.
    return meters / 1000.0 if meters > 200 else meters


def _duration_min(record: dict[str, Any]) -> float:
    minutes = _as_float(
        _pick(
            record,
            "duration_min",
            "durationMinutes",
            "durationInMinutes",
        )
    )
    if minutes is not None:
        return minutes

    seconds = _as_float(
        _pick(
            record,
            "duration_s",
            "durationSeconds",
            "duration",
            "totalDuration",
        )
    )
    if seconds is None:
        return 0.0
    return seconds / 60.0 if seconds > 300 else seconds


def _start_time(record: dict[str, Any]) -> Any:
    return _pick(
        record,
        "start_time",
        "startDate",
        "start",
        "date",
        "workoutStartDate",
        "startDateLocal",
    )


def _records_from_json(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]

    if isinstance(payload, dict):
        for key in ("workouts", "data", "items", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        return [payload]

    return []


def _normalize_records(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for rec in records:
        activity = str(
            _pick(rec, "activityType", "workoutActivityType", "type", "sport")
            or ""
        ).lower()
        if activity and ("run" not in activity and "course" not in activity):
            continue

        row = {
            "start_time": _start_time(rec),
            "distance_km": _distance_km(rec),
            "duration_min": _duration_min(rec),
            "avg_hr": _as_float(_pick(rec, "avg_hr", "averageHeartRate", "avgHeartRate")),
            "z1_min": _as_float(_pick(rec, "z1_min", "z1"), 0.0),
            "z2_min": _as_float(_pick(rec, "z2_min", "z2"), 0.0),
            "z3_min": _as_float(_pick(rec, "z3_min", "z3"), 0.0),
            "z4_min": _as_float(_pick(rec, "z4_min", "z4"), 0.0),
            "z5_min": _as_float(_pick(rec, "z5_min", "z5"), 0.0),
            "elevation_m": _as_float(
                _pick(rec, "elevation_m", "elevationGain", "totalAscent")
            ),
            "active_kcal": _as_float(
                _pick(rec, "active_kcal", "activeEnergyBurned", "activeEnergy")
            ),
        }

        if row["start_time"] is None:
            continue

        rows.append(row)

    return pd.DataFrame(rows)


def _assert_import_token(request: Request):
    expected = get_settings().import_api_token
    if not expected:
        return
    provided = request.headers.get("X-Import-Token", "").strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="invalid import token")


@router.post("/import-apple-health")
async def import_apple_health(
    request: Request,
    file: UploadFile | None = File(default=None),
    user_id: str | None = None,
):
    _assert_import_token(request)

    if file is not None:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="empty file")

        name = (file.filename or "").lower()
        if name.endswith(".csv"):
            df = pd.read_csv(BytesIO(content))
        else:
            try:
                payload = json.loads(content.decode("utf-8"))
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"invalid json file: {exc}")
            df = _normalize_records(_records_from_json(payload))
    else:
        try:
            payload = await request.json()
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"provide multipart file or json body: {exc}",
            )
        df = _normalize_records(_records_from_json(payload))

    if df.empty:
        return {"status": "empty", "inserted": 0, "duplicates": 0, "invalid_rows": 0}

    return import_sessions_dataframe(df, user_id=user_id)
