from datetime import datetime, timedelta
from statistics import mean, pstdev
from sqlalchemy.orm import Session

from models.models import RunSession
from schemas.signature import (
    RunnerSignature,
    SignaturePeriod,
    VolumeSignature,
    FrequencySignature,
    DurationSignature,
    IntensitySignature,
    LoadSignature,
    RegularitySignature,
    RobustnessSignature,
    AdaptationSignature,
)


def build_runner_signature(
    db: Session,
    user_id,
    weeks: int = 52,
) -> RunnerSignature:
    """
    Construit la RunnerSignature STRICTEMENT depuis la DB
    """

    end = datetime.utcnow()
    start = end - timedelta(weeks=weeks)

    # --------------------------------------------------
    # 1️⃣ Charger toutes les sessions
    # --------------------------------------------------
    sessions = (
        db.query(RunSession)
        .filter(
            RunSession.user_id == user_id,
            RunSession.start_time >= start,
            RunSession.start_time < end,
        )
        .all()
    )

    # --------------------------------------------------
    # 2️⃣ Grouper par semaine
    # --------------------------------------------------
    weekly = {}

    for s in sessions:
        week = s.start_time.isocalendar()[1]
        weekly.setdefault(week, []).append(s)

    weekly_km = []
    weekly_sessions = []
    weekly_duration = []
    weekly_load = []

    for runs in weekly.values():
        weekly_km.append(sum(r.distance_km for r in runs))
        weekly_sessions.append(len(runs))
        weekly_duration.append(sum(r.duration_min for r in runs))

        load = 0.0
        for r in runs:
            intense = (r.z4_min + r.z5_min) / max(r.duration_min, 1)
            load += r.duration_min * (1 + 2 * intense)

        weekly_load.append(load)

    # --------------------------------------------------
    # 3️⃣ Calculs simples
    # --------------------------------------------------
    volume = VolumeSignature(
        weekly_avg_km=mean(weekly_km) if weekly_km else 0,
        weekly_std_km=pstdev(weekly_km) if len(weekly_km) > 1 else 0,
        trend_12w_pct=0.0,  # TODO plus tard
    )

    frequency = FrequencySignature(
        weekly_avg_sessions=mean(weekly_sessions) if weekly_sessions else 0,
        weekly_std_sessions=pstdev(weekly_sessions) if len(weekly_sessions) > 1 else 0,
    )

    duration = DurationSignature(
        weekly_avg_min=mean(weekly_duration) if weekly_duration else 0,
        weekly_std_min=pstdev(weekly_duration) if len(weekly_duration) > 1 else 0,
    )

    # --------------------------------------------------
    # 4️⃣ Signatures vides (pour compatibilité)
    # --------------------------------------------------
    intensity = IntensitySignature(
        z4_z5_avg_pct=0,
        z4_z5_trend_12w_pct=0,
        z1_z3_avg_pct=0,
    )

    load = LoadSignature(
        weekly_avg_load=mean(weekly_load) if weekly_load else 0,
        weekly_std_load=pstdev(weekly_load) if len(weekly_load) > 1 else 0,
        acwr_avg=0,
        acwr_max=0,
    )

    regularity = RegularitySignature(
        weeks_with_runs_pct=len(weekly) / weeks if weeks > 0 else 0,
        longest_break_days=0,
    )

    robustness = RobustnessSignature(
        injury_free_weeks_pct=1.0,
        max_consecutive_weeks=len(weekly),
        breaks_over_7d_count=0,
    )

    adaptation = AdaptationSignature(
        load_std_trend_12w_pct=0,
    )

    # --------------------------------------------------
    # 5️⃣ Signature finale
    # --------------------------------------------------
    return RunnerSignature(
        period=SignaturePeriod(
            start=start.date().isoformat(),
            end=end.date().isoformat(),
            weeks=weeks,
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
