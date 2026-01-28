from typing import Optional, Dict, List
from pydantic import BaseModel
from pydantic import Field
from schemas.signature import RunnerSignature


class Period(BaseModel):
    start: str
    end: str


class WeeklyTotals(BaseModel):
    distance_km: float  # nombre de km
    duration_min: float  # temps de course en min
    sessions: int  # nombre de seance de running
    elevation_m: float  # le denivelé possitif lors des seances de running en metre
    avg_hr: Optional[float] = None  # frequence cardiaque moyenne en BPM


class TrainingLoad(BaseModel):
    load_7d: float  # Charge d’entraînement totale calculée sur les 7 derniers jours. (Somme des charges de chaque séance sur la période de 7 jours.)
    load_28d: float  # Charge d’entraînement cumulée sur les 28 derniers jours. (Représente la charge “habituelle” ou chronique.)
    ratio: float  # ratio = load_7d / load_28d


# La charge d’entraînement est un indicateur qui mesure l’effort réel fourni par ton corps sur une période donnée.
# Elle ne dépend pas seulement de la distance parcourue, mais aussi du temps passé à courir et de l’intensité de l’effort.
# La charge est calculée séance par séance, puis additionnée sur la période (par exemple une semaine).
# Pour chaque séance, on prend en compte deux éléments : La durée totale de la séance (en minutes) & La part de temps passée à haute intensité (zones cardiaques Z4 et Z5)

# calcul pour 1 seance :
# On calcule la part d’intensité élevée : Intensité élevée (%) =(temps en Z4 + temps en Z5) ÷ durée totale
# On applique cette intensité à la durée : Charge de la séance = durée × (1 + 2 × intensité élevée)
# Le facteur 2 signifie que les minutes à haute intensité comptent environ deux fois plus que les minutes faciles.


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

    model_config = {"populate_by_name": True}


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


class ChatRequest(BaseModel):
    message: str
    snapshot: Snapshot
    snapshots: Optional[SnapshotBatchPayload] = None
    meta: Optional[Dict[str, str]] = None
    signature: Optional[RunnerSignature] = None


# ======================================================
# 🏃‍♂️ RunSession Create Schema
# ======================================================

from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class RunSessionCreate(BaseModel):
    user_id: UUID
    start_time: datetime

    distance_km: float
    duration_min: float
    avg_hr: Optional[float] = None

    elevation_m: Optional[float] = None
    active_kcal: Optional[float] = None

    z1_min: float
    z2_min: float
    z3_min: float
    z4_min: float
    z5_min: float
