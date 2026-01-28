from services.periods import period_to_dates
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Dict


def load_snapshot(period_key):
    start, end = period_to_dates(period_key)

    return {
        "type": "REQUEST_SNAPSHOT",
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    }


def load_snapshots_for_comparison(left, right):
    return {
        "left": load_snapshot(left),
        "right": load_snapshot(right),
    }
