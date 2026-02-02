from sqlalchemy.orm import Session
from datetime import timedelta, date

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
    compute_acwr_series,
)


def build_runner_signature(db: Session, user_id) -> RunnerSignature:
    """
    Construit la signature long-terme du coureur
    sur une fenêtre glissante de 52 semaines,
    en excluant la semaine ISO en cours des trends.
    """
    print("🔥 build_runner_signature START")
    today = date.today()
    current_week = today.isocalendar()[:2]  # (year, week)

    # --------------------------------------------------
    # 0️⃣ Charger toutes les sessions
    # --------------------------------------------------
    all_sessions = (
        db.query(RunSession)
        .filter(RunSession.user_id == user_id)
        .order_by(RunSession.start_time.asc())
        .all()
    )

    if not all_sessions:
        raise ValueError("No run sessions found for user")

    # --------------------------------------------------
    # 1️⃣ Fenêtre temporelle 52 semaines
    # --------------------------------------------------
    end_dt = all_sessions[-1].start_time
    start_dt = end_dt - timedelta(weeks=52)

    sessions = [s for s in all_sessions if s.start_time >= start_dt]

    if not sessions:
        raise ValueError("No run sessions in the last 52 weeks")

    # --------------------------------------------------
    # 2️⃣ Découpage par semaine ISO
    # --------------------------------------------------
    completed_weeks: dict[tuple[int, int], list[RunSession]] = {}
    current_week_sessions = []

    for s in sessions:
        week_key = s.start_time.date().isocalendar()[:2]

        if week_key == current_week:
            current_week_sessions.append(s)
        else:
            completed_weeks.setdefault(week_key, []).append(s)

    # --------------------------------------------------
    # 3️⃣ Séries hebdomadaires (SEM. COMPLÈTES UNIQUEMENT)
    # --------------------------------------------------
    weekly_distances = [sum(s.distance_km for s in w) for w in completed_weeks.values()]

    weekly_durations = [
        sum(s.duration_min for s in w) for w in completed_weeks.values()
    ]

    weekly_sessions = [len(w) for w in completed_weeks.values()]

    # --------------------------------------------------
    # 4️⃣ Volume
    # --------------------------------------------------
    volume = VolumeSignature(
        weekly_avg_km=mean(weekly_distances),
        weekly_std_km=std(weekly_distances),
        trend_12w_pct=trend_pct(weekly_distances, window=12),
    )

    # --------------------------------------------------
    # 5️⃣ Durée
    # --------------------------------------------------
    duration = DurationSignature(
        weekly_avg_min=mean(weekly_durations),
        weekly_std_min=std(weekly_durations),
    )

    # --------------------------------------------------
    # 6️⃣ Fréquence
    # --------------------------------------------------
    frequency = FrequencySignature(
        weekly_avg_sessions=mean(weekly_sessions),
        weekly_std_sessions=std(weekly_sessions),
    )

    # --------------------------------------------------
    # 7️⃣ Intensité (calculée sur SESSIONS complètes)
    # --------------------------------------------------
    completed_sessions = [s for w in completed_weeks.values() for s in w]

    z4z5_ratios = [
        (s.z4_min + s.z5_min) / max(s.duration_min, 1) for s in completed_sessions
    ]

    z1z3_ratios = [
        (s.z1_min + s.z2_min + s.z3_min) / max(s.duration_min, 1)
        for s in completed_sessions
    ]

    intensity = IntensitySignature(
        z4_z5_avg_pct=mean(z4z5_ratios),
        z4_z5_trend_12w_pct=trend_pct(z4z5_ratios, window=12),
        z1_z3_avg_pct=mean(z1z3_ratios),
    )

    # --------------------------------------------------
    # 8️⃣ Charge (hebdomadaire, semaines complètes)
    # --------------------------------------------------
    weekly_loads = [
        sum(
            s.duration_min * (1 + 2 * ((s.z4_min + s.z5_min) / max(s.duration_min, 1)))
            for s in w
        )
        for w in completed_weeks.values()
    ]

    acwr_avg, acwr_max = compute_acwr_series(weekly_loads)

    load = LoadSignature(
        weekly_avg_load=mean(weekly_loads),
        weekly_std_load=std(weekly_loads),
        acwr_avg=acwr_avg,
        acwr_max=acwr_max,
    )

    # --------------------------------------------------
    # 9️⃣ Régularité
    # --------------------------------------------------
    weeks_with_runs_ratio = len(completed_weeks) / 52

    sorted_week_keys = sorted(completed_weeks.keys())

    longest_break_weeks = 0
    current_break = 0

    for i in range(1, len(sorted_week_keys)):
        prev_year, prev_week = sorted_week_keys[i - 1]
        curr_year, curr_week = sorted_week_keys[i]

        gap = (curr_year - prev_year) * 52 + (curr_week - prev_week) - 1

        if gap > 0:
            current_break += gap
            longest_break_weeks = max(longest_break_weeks, current_break)
        else:
            current_break = 0

    regularity = RegularitySignature(
        weeks_with_runs_pct=weeks_with_runs_ratio,
        longest_break_days=longest_break_weeks * 7,
    )

    # --------------------------------------------------
    # 🔟 Robustesse
    # --------------------------------------------------
    breaks_over_7d = longest_break_weeks

    injury_free_weeks_ratio = max(0.0, 1 - (breaks_over_7d / 52))

    robustness = RobustnessSignature(
        injury_free_weeks_pct=injury_free_weeks_ratio,
        max_consecutive_weeks=len(completed_weeks),
        breaks_over_7d_count=breaks_over_7d,
    )

    # --------------------------------------------------
    # 1️⃣1️⃣ Adaptation
    # --------------------------------------------------
    adaptation = AdaptationSignature(
        load_std_trend_12w_pct=trend_pct(weekly_loads, window=12),
    )

    # --------------------------------------------------
    # 1️⃣2️⃣ Signature finale
    # --------------------------------------------------
    return RunnerSignature(
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
