def extract_metric(snapshot, metric: str) -> float:
    metric = metric.upper()

    if metric == "DISTANCE":
        return snapshot.totals.distance_km

    if metric == "DURATION":
        return snapshot.totals.duration_min

    if metric == "SESSIONS":
        return snapshot.totals.sessions

    return 0.0


def compare_snapshots(left, right, metric: str) -> float:
    left_value = extract_metric(left, metric)
    right_value = extract_metric(right, metric)
    return left_value - right_value
