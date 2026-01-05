from services.periods import period_to_dates


def load_snapshot(period_key: str):
    start, end = period_to_dates(period_key)

    # ⛔ À ADAPTER à ton infra existante
    return {
        "type": "REQUEST_SNAPSHOT",
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    }


def load_snapshots_for_comparison(left: str, right: str):
    return {
        "left": load_snapshot(left),
        "right": load_snapshot(right),
    }
