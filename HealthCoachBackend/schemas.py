from typing import Optional, Dict, List
from pydantic import BaseModel
from pydantic import Field


class Period(BaseModel):
    start: str
    end: str


class WeeklyTotals(BaseModel):
    distance_km: float
    duration_min: float
    sessions: int
    elevation_m: float
    avg_hr: Optional[float] = None


class TrainingLoad(BaseModel):
    load_7d: float
    load_28d: float
    ratio: float


class DailyRun(BaseModel):
    date: str
    distance_km: float
    duration_min: float
    elevation_m: float
    avg_hr: float
    z1: float
    z2: float
    z3: float
    z4: float
    z5: float


class WeeklySnapshot(BaseModel):
    week_label: str
    period: Period
    totals: WeeklyTotals
    zones_percent: dict[str, float] = Field(default_factory=dict)
    daily_runs: list[DailyRun] = Field(alias="dailyRuns")
    training_load: TrainingLoad | None = None
    comparison_prev_week: dict[str, float] | None = None

    class Config:
        allow_population_by_field_name = True


class Snapshot(BaseModel):
    period: Period
    totals: WeeklyTotals
    daily_runs: list[DailyRun] = Field(default_factory=list, alias="dailyRuns")
    training_load: Optional[TrainingLoad] = None
    zones_percent: dict[str, float] | None = None
    longest_run_km: float | None = None

    class Config:
        allow_population_by_field_name = True


class SnapshotBatchPayload(BaseModel):
    left: Snapshot
    right: Snapshot


# ======================================================
# 🧠 RUNNER SIGNATURE (LONG-TERM PROFILE)
# ======================================================


class SignaturePeriod(BaseModel):
    start: str
    end: str
    weeks: int


class VolumeSignature(BaseModel):
    weekly_avg_km: float
    weekly_std_km: float
    trend_12w_pct: float


class DurationSignature(BaseModel):
    weekly_avg_min: float
    weekly_std_min: float


class FrequencySignature(BaseModel):
    weekly_avg_sessions: float
    weekly_std_sessions: float


class IntensitySignature(BaseModel):
    z4_z5_avg_pct: float
    z4_z5_trend_12w_pct: float
    z1_z3_avg_pct: float


class LoadSignature(BaseModel):
    weekly_avg_load: float
    weekly_std_load: float
    acwr_avg: float
    acwr_max: float


class RegularitySignature(BaseModel):
    weeks_with_runs_pct: float
    longest_break_days: int


class RunnerSignature(BaseModel):
    period: SignaturePeriod
    volume: VolumeSignature
    duration: DurationSignature
    frequency: FrequencySignature
    intensity: IntensitySignature
    load: LoadSignature
    regularity: RegularitySignature


# ======================================================


class ChatRequest(BaseModel):
    message: str
    snapshot: Snapshot
    snapshots: Optional[SnapshotBatchPayload] = None
    meta: Optional[Dict[str, str]] = None

    # 🆕 PROFIL LONG TERME
    signature: Optional[RunnerSignature] = None
