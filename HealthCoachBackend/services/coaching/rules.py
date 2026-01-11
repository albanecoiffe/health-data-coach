# services/coaching/rules.py


def analyze_regularity(signature: dict):
    reg = signature.get("regularity", {})
    freq = signature.get("frequency", {})

    return {
        "weeks_with_runs_pct": reg.get("weeks_with_runs_pct"),
        "longest_break_days": reg.get("longest_break_days"),
        "weekly_std_sessions": freq.get("weekly_std_sessions"),
    }


def analyze_volume(snapshot, signature: dict):
    return {
        "weekly_km": snapshot.totals.distance_km if snapshot else None,
        "habit_km": signature.get("volume", {}).get("weekly_avg_km"),
        "weekly_std_km": signature.get("volume", {}).get("weekly_std_km"),
    }


# services/coaching/rules.py


def analyze_load(snapshot, signature: dict):
    if not snapshot or not snapshot.training_load:
        return None

    load = signature.get("load", {})

    return {
        "weekly_avg_load": load.get("weekly_avg_load"),
        "weekly_std_load": load.get("weekly_std_load"),
        "acwr_avg": load.get("acwr_avg"),
        "acwr_max": load.get("acwr_max"),
    }
