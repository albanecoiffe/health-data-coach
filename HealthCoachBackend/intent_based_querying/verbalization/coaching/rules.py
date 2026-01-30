def analyze_regularity(signature: dict) -> dict:
    """
    Analyse la régularité long-terme à partir de la signature 52 semaines.
    Aucun jugement, aucun seuil médical.
    """

    regularity = signature.get("regularity", {})

    weeks_with_runs_pct = regularity.get("weeks_with_runs_pct")
    longest_break_days = regularity.get("longest_break_days")
    weekly_std_sessions = regularity.get("weekly_std_sessions")

    if weeks_with_runs_pct is None or longest_break_days is None:
        return {}

    return {
        "weeks_with_runs_pct": round(weeks_with_runs_pct, 3),
        "longest_break_days": int(longest_break_days),
        "weekly_std_sessions": (
            round(weekly_std_sessions, 2) if weekly_std_sessions is not None else None
        ),
    }


def analyze_volume(snapshot: dict, signature: dict) -> dict:
    """
    Analyse le volume récent par rapport à l'habitude long-terme.
    """

    volume_sig = signature.get("volume", {})

    weekly_avg_km = volume_sig.get("weekly_avg_km")
    weekly_std_km = volume_sig.get("weekly_std_km")
    trend_12w_pct = volume_sig.get("trend_12w_pct")

    current_week_km = snapshot.get("total_distance_km")

    if weekly_avg_km is None or current_week_km is None:
        return {}

    return {
        "current_week_km": round(current_week_km, 1),
        "weekly_avg_km": round(weekly_avg_km, 1),
        "weekly_std_km": (
            round(weekly_std_km, 1) if weekly_std_km is not None else None
        ),
        "trend_12w_pct": (
            round(trend_12w_pct, 3) if trend_12w_pct is not None else None
        ),
    }


def analyze_load(snapshot: dict, signature: dict) -> dict:
    """
    Analyse la charge récente par rapport à la charge habituelle.
    """

    load_sig = signature.get("load", {})

    weekly_avg_load = load_sig.get("weekly_avg_load")
    weekly_std_load = load_sig.get("weekly_std_load")
    acwr_avg = load_sig.get("acwr_avg")
    acwr_max = load_sig.get("acwr_max")

    current_week_load = snapshot.get("total_load")

    if weekly_avg_load is None or current_week_load is None:
        return {}

    return {
        "current_week_load": round(current_week_load, 1),
        "weekly_avg_load": round(weekly_avg_load, 1),
        "weekly_std_load": (
            round(weekly_std_load, 1) if weekly_std_load is not None else None
        ),
        "acwr_avg": round(acwr_avg, 2) if acwr_avg is not None else None,
        "acwr_max": round(acwr_max, 2) if acwr_max is not None else None,
    }


def analyze_progress(signature: dict) -> dict:
    """
    Analyse la progression globale sur la base de la signature 52 semaines.
    La progression est une lecture combinée :
    - évolution du volume
    - tolérance de charge
    - continuité
    """

    volume = signature.get("volume", {})
    load = signature.get("load", {})
    regularity = signature.get("regularity", {})

    trend_12w_pct = volume.get("trend_12w_pct")
    acwr_avg = load.get("acwr_avg")
    acwr_max = load.get("acwr_max")
    weeks_with_runs_pct = regularity.get("weeks_with_runs_pct")
    longest_break_days = regularity.get("longest_break_days")

    if trend_12w_pct is None or weeks_with_runs_pct is None:
        return {}

    return {
        "trend_12w_pct": round(trend_12w_pct, 3),
        "acwr_avg": round(acwr_avg, 2) if acwr_avg is not None else None,
        "acwr_max": round(acwr_max, 2) if acwr_max is not None else None,
        "weeks_with_runs_pct": round(weeks_with_runs_pct, 3),
        "longest_break_days": int(longest_break_days)
        if longest_break_days is not None
        else None,
    }
