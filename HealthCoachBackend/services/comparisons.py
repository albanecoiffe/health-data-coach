from services.periods import normalize


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


def resolve_intent(message: str) -> str:
    msg = normalize(message)

    if any(
        k in msg for k in ["bilan", "resume", "résumé", "recap", "synthese", "stat"]
    ):
        return "SUMMARY"

    if any(k in msg for k in ["compare", "comparaison", "difference", "évolution"]):
        return "COMPARE"

    return "FACTUAL"


def infer_period_context_from_keys(key):
    """
    Détermine le contexte temporel :
    WEEK | MONTH | YEAR | None
    """
    if isinstance(key, dict):
        if "offset" in key:
            return "WEEK"
        if "month_offset" in key:
            return "MONTH"
        if "year_offset" in key:
            return "YEAR"
    return None
