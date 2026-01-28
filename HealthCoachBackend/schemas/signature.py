from pydantic import BaseModel, Field


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
    breaks_over_7d_count: int = Field(alias="breaks_over7d_count")

    model_config = {"populate_by_name": True}


class AdaptationSignature(BaseModel):
    load_std_trend_12w_pct: float = Field(alias="load_std_trend12w_pct")

    model_config = {"populate_by_name": True}


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
