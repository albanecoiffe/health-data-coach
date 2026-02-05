def compute_totals(sessions):
    total_distance = sum(s.distance_km for s in sessions)
    total_duration = sum(s.duration_min for s in sessions)
    total_elevation = sum((s.elevation_m or 0) for s in sessions)

    hr_values = [s.avg_hr for s in sessions if s.avg_hr is not None]
    avg_hr = sum(hr_values) / len(hr_values) if hr_values else None

    return {
        "distance_km": total_distance,
        "duration_min": total_duration,
        "sessions": len(sessions),
        "elevation_m": total_elevation,
        "avg_hr": avg_hr,
    }


def compute_zones_percent(sessions):
    z1 = sum(s.z1_min for s in sessions)
    z2 = sum(s.z2_min for s in sessions)
    z3 = sum(s.z3_min for s in sessions)
    z4 = sum(s.z4_min for s in sessions)
    z5 = sum(s.z5_min for s in sessions)

    total = z1 + z2 + z3 + z4 + z5

    if total == 0:
        return {}

    return {
        "z1": z1 / total,
        "z2": z2 / total,
        "z3": z3 / total,
        "z4": z4 / total,
        "z5": z5 / total,
    }


def compute_training_load(sessions):
    load = 0.0

    for s in sessions:
        intense_ratio = (s.z4_min + s.z5_min) / max(s.duration_min, 1)
        load += s.duration_min * (1 + 2 * intense_ratio)

    return load
