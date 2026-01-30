from datetime import date
import numpy as np

from services.run_weeks.loader import load_run_weeks
from services.run_sessions.loader import load_run_sessions

from recommendation.clustering import cluster_weeks, cluster_sessions
from recommendation.risk import compute_weekly_risk, risk_level_from_proba
from recommendation.schemas import WeekRecommendation

from recommendation.engine import (
    _build_week_template,
    _adjust_plan_by_risk,
    _adjust_with_done_sessions,
    enrich_plan_with_descriptions,
    summarize_done_sessions,
)

SESSION_LABELS = {
    0: "intensity",
    1: "easy",
    2: "endurance",
}


def execute_recommendation(db, user_id) -> WeekRecommendation:
    """
    Compute a weekly training recommendation based on RunWeek and RunSession tables.
    Fully DB-native orchestration.
    """

    # --------------------------------------------------
    # 1) LOAD DATA
    # --------------------------------------------------
    run_weeks = load_run_weeks(db, user_id)
    run_sessions = load_run_sessions(db, user_id)

    if not run_weeks:
        raise ValueError("Not enough history to compute recommendation")

    # --------------------------------------------------
    # 2) CURRENT WEEK CONTEXT
    # --------------------------------------------------
    today = date.today()
    current_year, current_week, _ = today.isocalendar()

    # séances réalisées cette semaine (toutes, même non clusterisées)
    current_week_all_sessions = [
        s
        for s in run_sessions
        if s["start_time"].date().isocalendar()[:2] == (current_year, current_week)
    ]

    # --------------------------------------------------
    # 3) COMPLETED WEEKS (exclude current week)
    # --------------------------------------------------
    completed_weeks = [
        w for w in run_weeks if (w.year, w.iso_week) < (current_year, current_week)
    ]

    # Il faut de l'historique de semaines complètes, sinon reco inutile
    if len(completed_weeks) < 3:
        raise ValueError("Need at least 3 completed weeks to compute recommendation")

    last_3w = completed_weeks[-3:]

    # --------------------------------------------------
    # 4) CLUSTERING
    # --------------------------------------------------
    # cluster dominant calculé sur semaines complétées (évite de polluer avec la semaine en cours)
    dominant_cluster = cluster_weeks(completed_weeks)

    clustered_sessions = cluster_sessions(run_sessions)

    # --------------------------------------------------
    # 5) TARGET SESSIONS (habit)
    # --------------------------------------------------
    avg_sessions = int(
        np.clip(
            round(np.mean([int(w.sessions_count or 0) for w in last_3w])),
            2,
            5,
        )
    )

    # --------------------------------------------------
    # 6) RISK COMPUTATION
    # --------------------------------------------------
    avg_risk_proba = compute_weekly_risk(last_3w)
    risk_level = risk_level_from_proba(avg_risk_proba)

    # --------------------------------------------------
    # 7) DONE SESSIONS (CURRENT WEEK)
    # --------------------------------------------------
    # types de séances faites (uniquement celles clusterisées, sinon unknown)
    done_types = []
    current_week_clustered = []

    for s in clustered_sessions:
        if s["start_time"].date().isocalendar()[:2] != (current_year, current_week):
            continue
        current_week_clustered.append(s)

        label = s.get("cluster_session")
        session_type = SESSION_LABELS.get(label, "unknown")
        done_types.append(session_type)

    done_sessions_summary = summarize_done_sessions(current_week_clustered)

    # IMPORTANT:
    # - "done count" = toutes les séances effectuées cette semaine, même si non clusterisées
    done_count_all = len(current_week_all_sessions)
    remaining_sessions_count = max(0, avg_sessions - done_count_all)

    # --------------------------------------------------
    # 8) BUILD BASE PLAN
    # --------------------------------------------------
    base_plan = _build_week_template(
        cluster_week=dominant_cluster,
        avg_sessions=avg_sessions,
        dist_df=None,
    )

    base_plan = _adjust_plan_by_risk(base_plan, avg_risk_proba)

    final_plan = _adjust_with_done_sessions(
        base_plan=base_plan,
        done_types=done_types,
        remaining_sessions_count=remaining_sessions_count,
    )

    enriched_remaining_plan = enrich_plan_with_descriptions(final_plan)

    # --------------------------------------------------
    # 9) WEEK COMPLETE ?
    # --------------------------------------------------
    week_complete = len(enriched_remaining_plan) == 0

    # --------------------------------------------------
    # 10) PREVIOUS WEEK SUMMARY
    # --------------------------------------------------
    last_week = completed_weeks[-1]
    previous_week_summary = {
        "sessions": int(last_week.sessions_count or 0),
        "distance_km": round(float(last_week.total_distance_km or 0.0), 1),
    }

    # --------------------------------------------------
    # 11) FINAL OUTPUT
    # --------------------------------------------------
    return {
        "target_sessions": avg_sessions,
        "dominant_week_cluster": int(dominant_cluster)
        if dominant_cluster is not None
        else 0,
        "avg_risk_last_3w": round(float(avg_risk_proba), 3),
        "risk_level": risk_level,
        "base_plan": base_plan,
        "adjusted_plan_remaining": final_plan,
        "done_sessions": done_types,
        "remaining_sessions": enriched_remaining_plan,
        "done_sessions_details": done_sessions_summary,
        "week_complete": week_complete,
        "previous_week_had_sessions": (int(last_week.sessions_count or 0) > 0),
        "previous_week_summary": previous_week_summary,
    }
