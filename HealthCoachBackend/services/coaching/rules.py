# services/coaching/rules.py


def analyze_regularity(signature):
    return {
        "weeks_with_runs_pct": signature.regularity.weeks_with_runs_pct,
        "longest_break_days": signature.regularity.longest_break_days,
        "weekly_std_sessions": signature.frequency.weekly_std_sessions,
    }


def analyze_volume(snapshot, signature):
    weekly = snapshot.totals.distance_km
    avg = signature.volume.weekly_avg_km

    if weekly > avg + 15:
        status = "HIGH"
    elif weekly < avg - 10:
        status = "LOW"
    else:
        status = "NORMAL"

    return {
        "status": status,
        "weekly_km": weekly,
        "habit_km": avg,
    }


def analyze_load(snapshot, signature):
    if not snapshot.training_load:
        return None

    ratio = snapshot.training_load.ratio

    if ratio is None:
        status = "UNKNOWN"
    elif ratio > 1.3:
        status = "HIGH"
    elif ratio < 0.8:
        status = "LOW"
    else:
        status = "NORMAL"

    return {
        "status": status,
        "acwr": ratio,
        "habit_load": signature.load.weekly_avg_load,
    }
