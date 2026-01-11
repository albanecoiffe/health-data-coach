# services/coaching/dispatcher.py

import re
from services.periods import normalize


def detect_coaching_type(message: str) -> str | None:
    msg = normalize(message)

    if re.search(r"\b(regulier|constance|habitude|routine)\b", msg):
        return "REGULARITY"

    if re.search(r"\b(trop|charge|fatigue|intensif)\b", msg):
        return "LOAD"

    if re.search(r"\b(km|volume|distance)\b", msg):
        return "VOLUME"

    return None
