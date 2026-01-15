import pandas as pd


CUTOFF_DATE = "2025-09-14"


def load_weeks(path="weeks_received.csv"):
    df = pd.read_csv(path)
    df["week_start"] = pd.to_datetime(df["week_start"])
    df["week_end"] = pd.to_datetime(df["week_end"])
    return df[df["week_start"] >= CUTOFF_DATE].reset_index(drop=True)


def load_sessions(path="sessions_received.csv"):
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= CUTOFF_DATE].reset_index(drop=True)
    df["week_start"] = df["date"].dt.to_period("W").apply(lambda r: r.start_time)
    return df
