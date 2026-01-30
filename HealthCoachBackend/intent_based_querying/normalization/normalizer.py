# intent_based_querying/normalizer.py
import json


def normalize_period(intent: dict) -> dict:
    """
    Normalize LLM period output into a strict backend format.
    """
    period = intent.get("period")

    # Case 1 — already structured (V2 OK)
    if isinstance(period, dict):
        return intent

    # Case 2 — relative days expressed loosely by LLM
    if period in {"relative days", "relative_day", "days_ago"}:
        value = intent.get("value")

        if value is None:
            raise ValueError("Missing value for relative days period")

        intent["period"] = {
            "type": "relative_days",
            "offset": -int(value),
        }
        intent.pop("value", None)
        return intent

    # Case 3 — known string periods (V1 compatibility)
    if isinstance(period, str):
        intent["period"] = period
        return intent

    raise ValueError(f"Unrecognized period format: {period}")


def normalize_metric(raw_metric: str) -> str:
    """
    Transforme une métrique LLM / utilisateur
    en clé interne canonique.
    """
    if not raw_metric:
        raise ValueError("Metric is empty")

    metric = raw_metric.strip().lower()

    mapping = {
        "distance": "distance_km",
        "km": "distance_km",
        "kilometers": "distance_km",
        "distance_km": "distance_km",
        "sessions": "sessions",
        "session": "sessions",
        "duration": "duration_min",
        "time": "duration_min",
        "duration_min": "duration_min",
        "avg_hr": "avg_hr",
        "heart_rate": "avg_hr",
        "fc": "avg_hr",
        "elevation": "elevation_m",
        "elevation_m": "elevation_m",
        "kcal": "active_kcal",
        "calories": "active_kcal",
        "active_kcal": "active_kcal",
    }

    if metric not in mapping:
        raise ValueError(f"Unsupported metric: {raw_metric}")

    return mapping[metric]


def normalize_metric_from_message(intent: dict) -> dict:
    message = intent.get("original_message", "").lower()

    if "km" in message or "kilomètre" in message:
        intent["metric"] = "distance_km"

    return intent


def safe_json_load(raw: str) -> dict:
    """
    Parse du JSON venant d'un LLM.
    Tolère les sorties incomplètes ou bruitées.
    """
    raw = raw.strip()

    # Cas simple
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Tentative de récupération entre { ... }
    start = raw.find("{")
    end = raw.rfind("}")

    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            pass

    # Tentative de fermeture automatique
    if raw.startswith("{") and not raw.endswith("}"):
        try:
            return json.loads(raw + "}")
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Invalid JSON from LLM:\n{raw}")
