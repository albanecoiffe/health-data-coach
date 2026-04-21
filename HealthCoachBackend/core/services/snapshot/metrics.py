from core.heart_rate_zones import (
    HEART_RATE_ZONES,
    high_intensity_minutes,
    zone_minutes,
)


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
    totals = {
        zone.id: sum(zone_minutes(s, (zone.id,)) for s in sessions)
        for zone in HEART_RATE_ZONES
    }
    total = sum(totals.values())

    if total == 0:
        return {}

    return {zone_id: minutes / total for zone_id, minutes in totals.items()}


def compute_training_load(sessions):
    load = 0.0

    for s in sessions:
        intense_ratio = high_intensity_minutes(s) / max(s.duration_min, 1)
        load += s.duration_min * (1 + 2 * intense_ratio)

    return load
