from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from schemas.signature import (
    AdaptationSignature,
    DurationSignature,
    FrequencySignature,
    IntensitySignature,
    LoadSignature,
    RegularitySignature,
    RobustnessSignature,
    RunnerSignature,
    SignaturePeriod,
    VolumeSignature,
)
from core.services.signature.metrics import compute_acwr_series, mean, std, trend_pct


@dataclass(frozen=True)
class SignatureMetricDefinition:
    key: str
    category: str
    label: str
    value_format: str
    description: str
    interpretation: str


SIGNATURE_METRIC_DEFINITIONS: tuple[SignatureMetricDefinition, ...] = (
    SignatureMetricDefinition(
        key="volume.weekly_avg_km",
        category="Volume",
        label="Volume hebdo moyen",
        value_format="km_1",
        description="Distance moyenne courue par semaine active sur la fenetre analysee.",
        interpretation="Plus la valeur est elevee, plus le volume habituel est important.",
    ),
    SignatureMetricDefinition(
        key="volume.weekly_std_km",
        category="Volume",
        label="Variabilite du volume",
        value_format="km_1",
        description="Ecart-type de la distance hebdomadaire sur les semaines actives.",
        interpretation="Une valeur basse traduit un volume stable, une valeur haute un volume plus irregulier.",
    ),
    SignatureMetricDefinition(
        key="volume.trend_12w_pct",
        category="Volume",
        label="Tendance volume 12 semaines",
        value_format="pct_signed_1",
        description="Evolution du volume moyen recent par rapport au bloc precedent de 12 semaines actives.",
        interpretation="Positive = volume recent en hausse, negative = baisse recente.",
    ),
    SignatureMetricDefinition(
        key="duration.weekly_avg_min",
        category="Duree",
        label="Duree hebdo moyenne",
        value_format="min_0",
        description="Temps d'entrainement moyen par semaine active.",
        interpretation="Mesure le temps total passe a courir sur une semaine typique.",
    ),
    SignatureMetricDefinition(
        key="duration.weekly_std_min",
        category="Duree",
        label="Variabilite de la duree",
        value_format="min_0",
        description="Ecart-type du temps d'entrainement hebdomadaire.",
        interpretation="Plus la valeur est basse, plus la duree d'entrainement reste stable d'une semaine a l'autre.",
    ),
    SignatureMetricDefinition(
        key="frequency.weekly_avg_sessions",
        category="Frequence",
        label="Seances hebdo moyennes",
        value_format="count_1",
        description="Nombre moyen de sorties par semaine active.",
        interpretation="Donne la frequence habituelle d'entrainement.",
    ),
    SignatureMetricDefinition(
        key="frequency.weekly_std_sessions",
        category="Frequence",
        label="Variabilite de la frequence",
        value_format="count_1",
        description="Ecart-type du nombre de seances hebdomadaires.",
        interpretation="Faible = routine stable, eleve = alternance entre semaines legeres et chargees.",
    ),
    SignatureMetricDefinition(
        key="intensity.z4_z5_avg_pct",
        category="Intensite",
        label="Part haute intensite moyenne",
        value_format="ratio_pct_0",
        description="Part moyenne d'une seance passee en Z4-Z5, rapportee a sa duree.",
        interpretation="Plus la valeur est haute, plus l'entrainement contient d'efforts intenses.",
    ),
    SignatureMetricDefinition(
        key="intensity.z4_z5_trend_12w_pct",
        category="Intensite",
        label="Tendance haute intensite 12 semaines",
        value_format="pct_signed_1",
        description="Evolution recente de la part d'intensite Z4-Z5 entre deux blocs successifs de 12 seances.",
        interpretation="Positive = plus d'intensite recemment, negative = entrainement plus aerobie.",
    ),
    SignatureMetricDefinition(
        key="intensity.z1_z3_avg_pct",
        category="Intensite",
        label="Part endurance moyenne",
        value_format="ratio_pct_0",
        description="Part moyenne d'une seance passee en Z1-Z3, rapportee a sa duree.",
        interpretation="Plus la valeur est haute, plus la base aerobie domine.",
    ),
    SignatureMetricDefinition(
        key="load.weekly_avg_load",
        category="Charge",
        label="Charge hebdo moyenne",
        value_format="load_0",
        description="Charge d'entrainement moyenne, combinant duree et poids de la haute intensite.",
        interpretation="Permet de suivre le niveau global de sollicitation semaine apres semaine.",
    ),
    SignatureMetricDefinition(
        key="load.weekly_std_load",
        category="Charge",
        label="Variabilite de charge",
        value_format="load_0",
        description="Ecart-type de la charge hebdomadaire.",
        interpretation="Une valeur elevee signale des variations marquées de charge.",
    ),
    SignatureMetricDefinition(
        key="load.acwr_avg",
        category="Charge",
        label="ACWR moyen",
        value_format="ratio_2",
        description="Ratio moyen entre la charge d'une semaine et la moyenne des 4 semaines precedentes.",
        interpretation="Autour de 1 = charge stable, au-dessus = acceleration, en dessous = baisse.",
    ),
    SignatureMetricDefinition(
        key="load.acwr_max",
        category="Charge",
        label="ACWR max",
        value_format="ratio_2",
        description="Pic maximal du ratio charge semaine / moyenne des 4 semaines precedentes.",
        interpretation="Repere les accelerations de charge les plus fortes sur la fenetre.",
    ),
    SignatureMetricDefinition(
        key="regularity.weeks_with_runs_pct",
        category="Regularite",
        label="Semaines avec course",
        value_format="ratio_pct_0",
        description="Part des 52 semaines glissantes contenant au moins une sortie.",
        interpretation="Plus la valeur est proche de 100 %, plus l'entrainement est continu.",
    ),
    SignatureMetricDefinition(
        key="regularity.longest_break_days",
        category="Regularite",
        label="Coupure max sans course (jours)",
        value_format="days_0",
        description="Plus longue interruption consecutive sans course, exprimee en jours theoriques.",
        interpretation="Permet de voir la duree maximale d'arret dans la routine d'entrainement.",
    ),
    SignatureMetricDefinition(
        key="robustness.injury_free_weeks_pct",
        category="Robustesse",
        label="Semaines sans coupure",
        value_format="ratio_pct_0",
        description="Part estimee des 52 semaines sans semaine totalement vide.",
        interpretation="Plus la valeur est haute, plus l'entrainement a ete maintenu sans trou majeur.",
    ),
    SignatureMetricDefinition(
        key="robustness.max_consecutive_weeks",
        category="Robustesse",
        label="Serie active max",
        value_format="weeks_0",
        description="Nombre maximal de semaines consecutives avec au moins une sortie.",
        interpretation="Mesure la capacite a enchainer durablement les semaines actives.",
    ),
    SignatureMetricDefinition(
        key="robustness.breaks_over7d_count",
        category="Robustesse",
        label="Coupures > 7 jours",
        value_format="count_0",
        description="Nombre de sequences d'au moins une semaine pleine sans course.",
        interpretation="Plus la valeur est basse, plus la continuite de pratique est bonne.",
    ),
    SignatureMetricDefinition(
        key="adaptation.load_std_trend12w_pct",
        category="Adaptation",
        label="Tendance variabilite de charge 12 semaines",
        value_format="pct_signed_1",
        description="Evolution recente de la variabilite de charge, mesuree via l'ecart-type glissant 4 semaines.",
        interpretation="Positive = charge plus heurtée recemment, negative = charge plus lisse et maitrisée.",
    ),
)


def _week_start(series: pd.Series) -> pd.Series:
    normalized = pd.to_datetime(series).dt.normalize()
    return normalized - pd.to_timedelta(normalized.dt.weekday, unit="D")


def _prepare_sessions(df: pd.DataFrame) -> pd.DataFrame:
    prepared = df.copy()
    prepared["start_time"] = pd.to_datetime(prepared["start_time"])

    numeric_cols = (
        "distance_km",
        "duration_min",
        "avg_hr",
        "elevation_m",
        "active_kcal",
        "z1_min",
        "z2_min",
        "z3_min",
        "z4_min",
        "z5_min",
    )
    for col in numeric_cols:
        if col not in prepared.columns:
            prepared[col] = 0.0
        prepared[col] = pd.to_numeric(prepared[col], errors="coerce").fillna(0.0)

    prepared["high_intensity_min"] = prepared["z4_min"] + prepared["z5_min"]
    prepared["low_intensity_min"] = prepared["z1_min"] + prepared["z2_min"] + prepared["z3_min"]
    prepared["session_high_ratio"] = prepared["high_intensity_min"].div(
        prepared["duration_min"].replace(0, pd.NA)
    ).fillna(0.0)
    prepared["session_low_ratio"] = prepared["low_intensity_min"].div(
        prepared["duration_min"].replace(0, pd.NA)
    ).fillna(0.0)
    prepared["session_load"] = prepared["duration_min"] * (1 + 2 * prepared["session_high_ratio"])

    iso = prepared["start_time"].dt.isocalendar()
    prepared["iso_year"] = iso["year"].astype(int)
    prepared["iso_week"] = iso["week"].astype(int)
    prepared["week_start"] = _week_start(prepared["start_time"])

    return prepared.sort_values("start_time").reset_index(drop=True)


def _build_full_weekly_frame(
    sessions: pd.DataFrame,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
    current_week: tuple[int, int],
) -> pd.DataFrame:
    completed_sessions = sessions.loc[
        ~(
            (sessions["iso_year"] == current_week[0])
            & (sessions["iso_week"] == current_week[1])
        )
    ].copy()

    aggregates = (
        completed_sessions.groupby("week_start", as_index=False)
        .agg(
            distance_km=("distance_km", "sum"),
            duration_min=("duration_min", "sum"),
            sessions_count=("start_time", "size"),
            high_intensity_min=("high_intensity_min", "sum"),
            low_intensity_min=("low_intensity_min", "sum"),
            weekly_load=("session_load", "sum"),
        )
        .sort_values("week_start")
    )

    first_week_start = start_dt.normalize() - pd.Timedelta(days=start_dt.weekday())
    last_week_start = end_dt.normalize() - pd.Timedelta(days=end_dt.weekday())
    if end_dt.isocalendar()[:2] == current_week:
        last_week_start = last_week_start - timedelta(days=7)

    if last_week_start < first_week_start:
        return pd.DataFrame(
            columns=[
                "week_start",
                "distance_km",
                "duration_min",
                "sessions_count",
                "high_intensity_min",
                "low_intensity_min",
                "weekly_load",
            ]
        )

    full_index = pd.date_range(start=first_week_start, end=last_week_start, freq="W-MON")
    weekly = (
        aggregates.set_index("week_start")
        .reindex(full_index, fill_value=0.0)
        .rename_axis("week_start")
        .reset_index()
    )
    weekly["sessions_count"] = weekly["sessions_count"].astype(int)
    weekly["had_run"] = weekly["sessions_count"] > 0
    weekly["high_intensity_pct"] = weekly["high_intensity_min"].div(
        weekly["duration_min"].replace(0, pd.NA)
    ).fillna(0.0)
    weekly["low_intensity_pct"] = weekly["low_intensity_min"].div(
        weekly["duration_min"].replace(0, pd.NA)
    ).fillna(0.0)
    weekly["distance_rolling_4w"] = weekly["distance_km"].rolling(4, min_periods=1).mean()
    weekly["duration_rolling_4w"] = weekly["duration_min"].rolling(4, min_periods=1).mean()
    weekly["sessions_rolling_4w"] = weekly["sessions_count"].rolling(4, min_periods=1).mean()
    weekly["load_rolling_4w"] = weekly["weekly_load"].rolling(4, min_periods=1).mean()
    weekly["load_std_rolling_4w"] = (
        weekly["weekly_load"].rolling(4, min_periods=2).std(ddof=0).fillna(0.0)
    )
    weekly["active_weeks_rolling_4w"] = (
        weekly["had_run"].astype(float).rolling(4, min_periods=1).mean()
    )

    acwr_series: list[float] = []
    weekly_loads = weekly["weekly_load"].tolist()
    for idx, acute in enumerate(weekly_loads):
        if idx < 4:
            acwr_series.append(0.0)
            continue
        chronic = mean(weekly_loads[idx - 4 : idx])
        acwr_series.append(acute / chronic if chronic > 0 else 0.0)
    weekly["acwr"] = acwr_series

    active_streak = 0
    break_streak = 0
    active_streak_values: list[int] = []
    break_streak_values: list[int] = []
    break_group_count = 0
    in_break = False

    for had_run in weekly["had_run"].tolist():
        if had_run:
            active_streak += 1
            break_streak = 0
            in_break = False
        else:
            break_streak += 1
            active_streak = 0
            if not in_break:
                break_group_count += 1
                in_break = True

        active_streak_values.append(active_streak)
        break_streak_values.append(break_streak * 7)

    weekly["active_streak_weeks"] = active_streak_values
    weekly["break_streak_days"] = break_streak_values
    weekly.attrs["break_group_count"] = break_group_count

    return weekly


def build_runner_signature_from_dataframe(
    df: pd.DataFrame,
    *,
    today: date | None = None,
) -> tuple[RunnerSignature, pd.DataFrame]:
    if df.empty:
        raise ValueError("No run sessions found for user")

    today = today or date.today()
    current_week = today.isocalendar()[:2]

    sessions = _prepare_sessions(df)
    end_dt = sessions["start_time"].max()
    start_dt = end_dt - pd.Timedelta(weeks=52)
    sessions = sessions.loc[sessions["start_time"] >= start_dt].copy()

    if sessions.empty:
        raise ValueError("No run sessions in the last 52 weeks")

    weekly = _build_full_weekly_frame(sessions, start_dt, end_dt, current_week)
    active_weeks = weekly.loc[weekly["had_run"]].copy()
    completed_sessions = sessions.loc[
        ~(
            (sessions["iso_year"] == current_week[0])
            & (sessions["iso_week"] == current_week[1])
        )
    ].copy()

    volume = VolumeSignature(
        weekly_avg_km=mean(active_weeks["distance_km"].tolist()),
        weekly_std_km=std(active_weeks["distance_km"].tolist()),
        trend_12w_pct=trend_pct(active_weeks["distance_km"].tolist(), window=12),
    )
    duration = DurationSignature(
        weekly_avg_min=mean(active_weeks["duration_min"].tolist()),
        weekly_std_min=std(active_weeks["duration_min"].tolist()),
    )
    frequency = FrequencySignature(
        weekly_avg_sessions=mean(active_weeks["sessions_count"].tolist()),
        weekly_std_sessions=std(active_weeks["sessions_count"].tolist()),
    )
    intensity = IntensitySignature(
        z4_z5_avg_pct=mean(completed_sessions["session_high_ratio"].tolist()),
        z4_z5_trend_12w_pct=trend_pct(
            completed_sessions["session_high_ratio"].tolist(),
            window=12,
        ),
        z1_z3_avg_pct=mean(completed_sessions["session_low_ratio"].tolist()),
    )

    weekly_loads = active_weeks["weekly_load"].tolist()
    acwr_avg, acwr_max = compute_acwr_series(weekly_loads)
    load = LoadSignature(
        weekly_avg_load=mean(weekly_loads),
        weekly_std_load=std(weekly_loads),
        acwr_avg=acwr_avg,
        acwr_max=acwr_max,
    )

    longest_break_days = int(weekly["break_streak_days"].max()) if not weekly.empty else 0
    weeks_with_runs_ratio = float(weekly["had_run"].sum()) / 52 if not weekly.empty else 0.0
    regularity = RegularitySignature(
        weeks_with_runs_pct=weeks_with_runs_ratio,
        longest_break_days=longest_break_days,
    )

    inactive_weeks = int((~weekly["had_run"]).sum()) if not weekly.empty else 0
    robustness = RobustnessSignature(
        injury_free_weeks_pct=max(0.0, 1 - (inactive_weeks / 52)),
        max_consecutive_weeks=int(weekly["active_streak_weeks"].max()) if not weekly.empty else 0,
        breaks_over_7d_count=int(weekly.attrs.get("break_group_count", 0)),
    )

    load_std_series = active_weeks["weekly_load"].rolling(4, min_periods=2).std(ddof=0).fillna(0.0)
    adaptation = AdaptationSignature(
        load_std_trend_12w_pct=trend_pct(load_std_series.tolist(), window=12),
    )

    signature = RunnerSignature(
        period=SignaturePeriod(
            start=start_dt.date().isoformat(),
            end=end_dt.date().isoformat(),
            weeks=52,
        ),
        volume=volume,
        duration=duration,
        frequency=frequency,
        intensity=intensity,
        load=load,
        regularity=regularity,
        robustness=robustness,
        adaptation=adaptation,
    )
    return signature, weekly
