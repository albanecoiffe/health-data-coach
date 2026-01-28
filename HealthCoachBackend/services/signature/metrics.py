import numpy as np


def mean(values):
    return float(np.mean(values)) if values else 0.0


def std(values):
    return float(np.std(values)) if values else 0.0


def trend_pct(old, new):
    if old == 0:
        return 0.0
    return ((new - old) / old) * 100


def compute_acwr(load_7d, load_28d):
    if load_28d == 0:
        return 0.0
    return load_7d / load_28d
