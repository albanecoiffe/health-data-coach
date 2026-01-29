from sqlalchemy.orm import Session
from datetime import timedelta

from models.RunSession import RunSession
from schemas.signature import (
    RunnerSignature,
    SignaturePeriod,
    VolumeSignature,
    DurationSignature,
    FrequencySignature,
    IntensitySignature,
    LoadSignature,
    RegularitySignature,
    RobustnessSignature,
    AdaptationSignature,
)

from services.signature.metrics import (
    mean,
    std,
    trend_pct,
    compute_acwr,
)


def build_runner_signature(db: Session, user_id) -> RunnerSignature:
    """
    Construit la signature long-terme du coureur (52 semaines)
    """

    sessions = (
        db.query(RunSession)
        .filter(RunSession.user_id == user_id)
        .order_by(RunSession.start_time.asc())
        .all()
    )

    if not sessions:
        raise ValueError("No run sessions found for user")

    # --------------------------------------------------
    # 1️⃣ Découpage par semaine
    # --------------------------------------------------
    weeks = {}
    for s in sessions:
        week_key = s.start_time.date().isocalendar()[:2]
        weeks.setdefault(week_key, []).append(s)

    weekly_distances = [sum(s.distance_km for s in w) for w in weeks.values()]
    weekly_durations = [sum(s.duration_min for s in w) for w in weeks.values()]
    weekly_sessions = [len(w) for w in weeks.values()]

    # --------------------------------------------------
    # 2️⃣ Volume / durée / fréquence
    # --------------------------------------------------
    volume = VolumeSignature(
        weekly_avg_km=mean(weekly_distances),
        weekly_std_km=std(weekly_distances),
        trend_12w_pct=0.0,
    )

    duration = DurationSignature(
        weekly_avg_min=mean(weekly_durations),
        weekly_std_min=std(weekly_durations),
    )

    frequency = FrequencySignature(
        weekly_avg_sessions=mean(weekly_sessions),
        weekly_std_sessions=std(weekly_sessions),
    )

    # --------------------------------------------------
    # 3️⃣ Intensité
    # --------------------------------------------------
    z4z5 = [(s.z4_min + s.z5_min) / max(s.duration_min, 1) for s in sessions]

    intensity = IntensitySignature(
        z4_z5_avg_pct=mean(z4z5),
        z4_z5_trend_12w_pct=0.0,
        z1_z3_avg_pct=0.0,
    )

    # --------------------------------------------------
    # 4️⃣ Charge
    # --------------------------------------------------
    weekly_loads = [
        sum(
            s.duration_min * (1 + 2 * ((s.z4_min + s.z5_min) / max(s.duration_min, 1)))
            for s in w
        )
        for w in weeks.values()
    ]

    load = LoadSignature(
        weekly_avg_load=mean(weekly_loads),
        weekly_std_load=std(weekly_loads),
        acwr_avg=0.0,
        acwr_max=0.0,
    )

    # --------------------------------------------------
    # 5️⃣ Régularité / robustesse
    # --------------------------------------------------
    regularity = RegularitySignature(
        weeks_with_runs_pct=len(weeks) / 52,
        longest_break_days=0,
    )

    robustness = RobustnessSignature(
        injury_free_weeks_pct=1.0,
        max_consecutive_weeks=len(weeks),
        breaks_over7d_count=0,
    )

    adaptation = AdaptationSignature(
        load_std_trend12w_pct=0.0,
    )

    # --------------------------------------------------
    # 6️⃣ Signature finale
    # --------------------------------------------------
    return RunnerSignature(
        period=SignaturePeriod(
            start=sessions[0].start_time.date().isoformat(),
            end=sessions[-1].start_time.date().isoformat(),
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
