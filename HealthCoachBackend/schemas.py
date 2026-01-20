from typing import Optional, Dict, List
from pydantic import BaseModel
from pydantic import Field


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
# 🧠 RUNNER SIGNATURE (LONG-TERM PROFILE) : 52 dernières semaines
# ======================================================


class SignaturePeriod(BaseModel):
    start: str
    end: str
    weeks: int


class VolumeSignature(BaseModel):
    weekly_avg_km: float  # Distance moyenne courue par semaine sur la période analysée.
    weekly_std_km: float  # Variabilité du volume hebdomadaire. Plus la valeur est élevée, plus l’entraînement est irrégulier.
    trend_12w_pct: float  # Évolution du volume sur les 12 dernières semaines (en %).


class DurationSignature(BaseModel):
    weekly_avg_min: float  # Durée moyenne d’entraînement par semaine.
    weekly_std_min: float  # Variabilité de la durée hebdomadaire.


class FrequencySignature(BaseModel):
    weekly_avg_sessions: float  # Nombre moyen de séances par semaine.
    weekly_std_sessions: float  # Régularité du nombre de séances.


class IntensitySignature(BaseModel):
    z4_z5_avg_pct: float  # Part moyenne du temps passé à haute intensité.
    z4_z5_trend_12w_pct: (
        float  # Évolution récente (sur les 12 dernieres semaines) de l’intensité.
    )
    z1_z3_avg_pct: float  # Part du temps passé en endurance / faible intensité.


class LoadSignature(BaseModel):
    weekly_avg_load: float  # Charge moyenne hebdomadaire. (volume, temps d’entraînement, intensité (z4+z5))
    weekly_std_load: float  # Variabilité de la charge.
    acwr_avg: float  # Ratio charge aiguë (4 sem) / chronique moyen (12 sem)
    acwr_max: float  # Pic maximal observé (zone de risque potentiel).


class RegularitySignature(BaseModel):
    weeks_with_runs_pct: float  # Pourcentage de semaines avec au moins une séance.
    longest_break_days: int


# La plus longue séquence de semaines consécutives sans aucune séance de running
# exprimée en jours théoriques (multiples de 7)
# 1 semaine sans séance → 7 jours
# 2 semaines consécutives sans séance → 14 jours


class RobustnessSignature(BaseModel):
    injury_free_weeks_pct: float
    max_consecutive_weeks: int
    breaks_over_7d_count: int = Field(
        alias="breaks_over7d_count"
    )  # Nombre de pauses supérieures à 7 jours.

    class Config:
        allow_population_by_field_name = True


class AdaptationSignature(BaseModel):
    load_std_trend_12w_pct: float = Field(alias="load_std_trend12w_pct")

    class Config:
        allow_population_by_field_name = True


class RunnerSignature(BaseModel):
    period: SignaturePeriod
    volume: VolumeSignature
    duration: DurationSignature
    frequency: FrequencySignature
    intensity: IntensitySignature
    load: LoadSignature
    regularity: RegularitySignature
    robustness: RobustnessSignature
    adaptation: AdaptationSignature


# ======================================================


class ChatRequest(BaseModel):
    message: str
    snapshot: Snapshot
    snapshots: Optional[SnapshotBatchPayload] = None
    meta: Optional[Dict[str, str]] = None
    signature: Optional[RunnerSignature] = None
