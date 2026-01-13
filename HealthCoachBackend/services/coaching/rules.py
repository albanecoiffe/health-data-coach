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
    volume = signature.get("volume", {})

    return {
        # Semaine courante
        "current_week_km": snapshot.totals.distance_km if snapshot else None,
        # Habitude long terme
        "weekly_avg_km": volume.get("weekly_avg_km"),
        "weekly_std_km": volume.get("weekly_std_km"),
        # Tendance récente
        "trend_12w_pct": volume.get("trend_12w_pct"),
    }


# services/coaching/rules.py


def analyze_load(snapshot, signature: dict):
    load = signature.get("load", {})
    if not load:
        return None

    return {
        "weekly_avg_load": load.get("weekly_avg_load"),
        "weekly_std_load": load.get("weekly_std_load"),
        "acwr_avg": load.get("acwr_avg"),
        "acwr_max": load.get("acwr_max"),
    }


def analyze_progress(signature: dict):
    volume = signature.get("volume", {})
    load = signature.get("load", {})
    regularity = signature.get("regularity", {})

    return {
        "trend_12w_pct": volume.get("trend_12w_pct"),
        "acwr_avg": load.get("acwr_avg"),
        "acwr_max": load.get("acwr_max"),
        "weeks_with_runs_pct": regularity.get("weeks_with_runs_pct"),
        "longest_break_days": regularity.get("longest_break_days"),
    }
