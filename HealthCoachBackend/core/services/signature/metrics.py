import numpy as np


def mean(values):
    return float(np.mean(values)) if values else 0.0


def std(values):
    return float(np.std(values)) if values else 0.0


def trend_pct(values, window=12):
    """
    Calcule la tendance (%) entre la moyenne des `window`
    dernières valeurs et les `window` précédentes.
    """
    if len(values) < window * 2:
        return 0.0

    recent = values[-window:]
    previous = values[-2 * window : -window]

    prev_mean = mean(previous)
    if prev_mean == 0:
        return 0.0

    return (mean(recent) - prev_mean) / prev_mean * 100


def compute_acwr_series(weekly_loads):
    """
    Calcule la série d'ACWR hebdomadaire à partir des charges hebdo.
    ACWR = load_week / mean(load_last_4_weeks)
    """
    acwrs = []

    for i in range(4, len(weekly_loads)):
        acute = weekly_loads[i]
        chronic = mean(weekly_loads[i - 4 : i])

        if chronic > 0:
            acwrs.append(acute / chronic)

    if not acwrs:
        return 0.0, 0.0

    return mean(acwrs), max(acwrs)
