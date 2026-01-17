# ============================================================
# Recommendation Engine — Running Coach
# ============================================================
import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

from recommendation.loader import load_weeks, load_sessions
from recommendation.risk import compute_weekly_risk, risk_level_from_proba
from recommendation.clustering import (
    cluster_weeks,
    cluster_sessions,
)
from recommendation.schemas import WeekRecommendation

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

CUTOFF_DATE = "2025-09-14"

SESSION_LABELS = {
    0: "intensity",
    1: "easy",
    2: "endurance",
}

FEATURES_WEEK = [
    "distance_km",
    "sessions",
    "duration_min",
    "weekly_load",
    "high_intensity_pct",
]

FEATURES_SESSION = [
    "distance_km",
    "duration_min",
    "pace_min_per_km",
    "low_intensity_pct",
    "high_intensity_pct",
]

# ============================================================
# Session type explanations — Running Coach
# ============================================================

SESSION_DESCRIPTIONS = {
    "easy": {
        "label": "Séance facile",
        "objective": "Récupération active et maintien du volume",
        "description": (
            "Sortie courte à allure confortable, réalisée majoritairement "
            "en basse intensité. La respiration doit rester facile et "
            "l’effort ne doit pas générer de fatigue notable."
        ),
        "physiology": "Faible stress cardiovasculaire et musculaire",
        "data_profile": {
            "avg_duration_min": 38,
            "avg_distance_km": 5.7,
            "low_intensity_pct": 0.92,
        },
    },
    "endurance": {
        "label": "Séance d’endurance",
        "objective": "Développement de l’endurance aérobie",
        "description": (
            "Sortie plus longue à allure modérée, majoritairement en basse intensité. "
            "L’objectif est de construire une base aérobie solide et "
            "d’améliorer la capacité à maintenir un effort dans le temps."
        ),
        "physiology": "Sollicitation aérobie prolongée, fatigue progressive",
        "data_profile": {
            "avg_duration_min": 76,
            "avg_distance_km": 11.8,
            "low_intensity_pct": 0.91,
        },
    },
    "intensity": {
        "label": "Séance intense",
        "objective": "Amélioration de la vitesse et de la capacité cardiovasculaire",
        "description": (
            "Séance structurée avec une part importante d’efforts à haute intensité "
            "(fractionné, tempo, blocs soutenus). "
            "Cette séance est exigeante et nécessite une récupération adéquate."
        ),
        "physiology": "Stress cardiovasculaire et neuromusculaire élevé",
        "data_profile": {
            "avg_duration_min": 66,
            "avg_distance_km": 11.1,
            "high_intensity_pct": 0.56,
        },
    },
}

SESSION_PROFILES = {
    "easy": {
        "label": "Séance facile",
        "data_profile": {
            "avg_duration_min": 38,
            "avg_distance_km": 5.7,
            "low_intensity_pct": 0.92,
            "high_intensity_pct": 0.08,
        },
    },
    "endurance": {
        "label": "Séance d’endurance",
        "data_profile": {
            "avg_duration_min": 76,
            "avg_distance_km": 11.8,
            "low_intensity_pct": 0.91,
            "high_intensity_pct": 0.09,
        },
    },
    "intensity": {
        "label": "Séance intense",
        "data_profile": {
            "avg_duration_min": 66,
            "avg_distance_km": 11.1,
            "low_intensity_pct": 0.44,
            "high_intensity_pct": 0.56,
        },
    },
}

# ------------------------------------------------------------
# MAIN ENTRY POINT
# ------------------------------------------------------------


def compute_week_recommendation_from_csv(
    weeks_path: str = "weeks_received.csv",
    sessions_path: str = "sessions_received.csv",
) -> WeekRecommendation:
    # --------------------------------------------------------
    # 1. LOAD DATA
    # --------------------------------------------------------

    weeks = load_weeks()
    sessions = load_sessions()

    # --------------------------------------------------------
    # 2. CLUSTER WEEKS
    # --------------------------------------------------------

    weeks_clustered = cluster_weeks(weeks)

    # --------------------------------------------------------
    # 3. CLUSTER SESSIONS
    # --------------------------------------------------------

    sessions_clustered = cluster_sessions(sessions)

    # --------------------------------------------------------
    # 4. SESSION DISTRIBUTION PER WEEK CLUSTER
    # --------------------------------------------------------

    distribution = _compute_session_distribution(sessions_clustered, weeks_clustered)

    # --------------------------------------------------------
    # 5. RISK SCORE (via risk.py)
    # --------------------------------------------------------

    risk_df = compute_weekly_risk(weeks_clustered)

    # --------------------------------------------------------
    # 6. CONTEXTE TEMPOREL — SEMAINE COURANTE
    # --------------------------------------------------------

    current_week_start = weeks_clustered["week_start"].max()

    # Par défaut, la semaine courante n'est PAS encore comptée
    completed_weeks = weeks_clustered[
        weeks_clustered["week_start"] < current_week_start
    ]

    last_3w = completed_weeks.tail(3)

    dominant_cluster = int(last_3w["cluster_week"].mode()[0])
    avg_sessions = int(np.clip(round(last_3w["sessions"].mean()), 2, 5))

    avg_risk = risk_df[risk_df["week_start"].isin(last_3w["week_start"])][
        "risk_proba"
    ].mean()

    risk_level = risk_level_from_proba(avg_risk)

    # Logs explicites — semaines utilisées
    print("\n📈 Weekly stats used for risk computation:")
    print(last_3w[["week_start"] + FEATURES_WEEK].to_string(index=False))

    print("📈 Avg risk proba (last 3w):", round(float(avg_risk), 3))

    # --------------------------------------------------------
    # 7. BUILD PLAN (semaine courante)
    # --------------------------------------------------------

    base_plan = _build_week_template(dominant_cluster, avg_sessions, distribution)
    base_plan = _adjust_plan_by_risk(base_plan, avg_risk)

    current_sessions = sessions_clustered[
        sessions_clustered["week_start"] == current_week_start
    ]

    done_types = current_sessions["cluster_session"].map(SESSION_LABELS).tolist()
    done_sessions_summary = summarize_done_sessions(current_sessions)

    remaining_sessions = max(0, avg_sessions - len(done_types))

    final_plan = _adjust_with_done_sessions(
        base_plan,
        done_types,
        remaining_sessions,
    )

    enriched_remaining_plan = enrich_plan_with_descriptions(final_plan)

    # --------------------------------------------------------
    # 8. DÉTECTION — SEMAINE COMPLÈTE ?
    # --------------------------------------------------------

    week_complete = len(enriched_remaining_plan) == 0

    # --------------------------------------------------------
    # 9. 🔄 SI SEMAINE COMPLÈTE → PLANIFIER SEMAINE SUIVANTE
    # --------------------------------------------------------

    if week_complete:
        print("\n🔄 SEMAINE COMPLÈTE → PLANIFICATION SEMAINE SUIVANTE")

        # 👉 la semaine courante devient historique
        completed_weeks = weeks_clustered[
            weeks_clustered["week_start"] <= current_week_start
        ]

        last_3w = completed_weeks.tail(3)

        dominant_cluster = int(last_3w["cluster_week"].mode()[0])
        avg_sessions = int(np.clip(round(last_3w["sessions"].mean()), 2, 5))

        avg_risk = risk_df[risk_df["week_start"].isin(last_3w["week_start"])][
            "risk_proba"
        ].mean()

        risk_level = risk_level_from_proba(avg_risk)

        print("\n📈 Weekly stats used for NEXT WEEK risk computation:")
        print(last_3w[["week_start"] + FEATURES_WEEK].to_string(index=False))
        print("📈 Avg risk proba (next week):", round(float(avg_risk), 3))

        # Nouvelle semaine vierge
        done_types = []
        done_sessions_summary = []

        base_plan = _build_week_template(dominant_cluster, avg_sessions, distribution)
        base_plan = _adjust_plan_by_risk(base_plan, avg_risk)

        final_plan = base_plan
        enriched_remaining_plan = enrich_plan_with_descriptions(final_plan)

    # --------------------------------------------------------
    # 10. DEBUG FINAL
    # --------------------------------------------------------

    print("\n================ DEBUG RECOMMENDATION ================")
    print("📅 Current week start:", current_week_start)
    print("🧠 Dominant cluster:", dominant_cluster)
    print("🎯 Target sessions:", avg_sessions)
    print("⚠️ Risk level:", risk_level)
    print("📈 Avg risk last 3w:", round(float(avg_risk), 3))
    print("✅ Week complete:", week_complete)
    print("🏷️ Done types:", done_types)
    print("🗓️ Remaining sessions:", enriched_remaining_plan)

    # --------------------------------------------------------
    # 11. OUTPUT
    # --------------------------------------------------------

    return {
        "target_sessions": avg_sessions,
        "dominant_week_cluster": dominant_cluster,
        "avg_risk_last_3w": round(float(avg_risk), 3),
        "risk_level": risk_level,
        "base_plan": base_plan,
        "adjusted_plan_remaining": final_plan,
        "done_sessions": done_types,
        "remaining_sessions": enriched_remaining_plan,
        "done_sessions_details": done_sessions_summary,
        "week_complete": week_complete,
    }


# ------------------------------------------------------------
# INTERNAL HELPERS (unchanged)
# ------------------------------------------------------------


def _cluster_weeks(df):
    df = df.dropna(subset=FEATURES_WEEK).copy()
    X = StandardScaler().fit_transform(df[FEATURES_WEEK])
    df["cluster_week"] = KMeans(n_clusters=3, random_state=42, n_init=20).fit_predict(X)
    return df


def _cluster_sessions(df):
    df = df.dropna(subset=FEATURES_SESSION).copy()
    X = StandardScaler().fit_transform(df[FEATURES_SESSION])
    df["cluster_session"] = KMeans(
        n_clusters=3, random_state=42, n_init=20
    ).fit_predict(X)
    return df


def summarize_done_sessions(current_sessions: pd.DataFrame) -> list[dict]:
    summaries = []

    for _, row in current_sessions.iterrows():
        summaries.append(
            {
                "type": SESSION_LABELS[row["cluster_session"]],
                "duration_min": round(row["duration_min"], 1),
                "distance_km": round(row["distance_km"], 1),
                "low_intensity_pct": round(row["low_intensity_pct"], 2),
                "high_intensity_pct": round(row["high_intensity_pct"], 2),
            }
        )

    return summaries


def _compute_session_distribution(sessions, weeks):
    counts = (
        sessions.groupby(["week_start", "cluster_session"])
        .size()
        .reset_index(name="n_sessions")
    )

    counts = counts.merge(
        weeks[["week_start", "cluster_week"]],
        on="week_start",
        how="left",
    )

    dist = (
        counts.groupby(["cluster_week", "cluster_session"])["n_sessions"]
        .mean()
        .reset_index()
    )

    dist["pct"] = dist.groupby("cluster_week")["n_sessions"].transform(
        lambda x: x / x.sum()
    )

    return dist


def _compute_risk_scores(df):
    df = df.dropna(subset=FEATURES_WEEK).copy()
    load_threshold = df["weekly_load"].quantile(0.80)

    def is_risky(row):
        return int(
            row["cluster_week"] == 1
            or row["weekly_load"] > load_threshold
            or row["high_intensity_pct"] > 0.45
        )

    df["risk"] = df.apply(is_risky, axis=1)

    X = df[FEATURES_WEEK]
    y = df["risk"]

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", LogisticRegression()),
        ]
    )

    model.fit(X, y)
    df["risk_proba"] = model.predict_proba(X)[:, 1]

    return df


def _build_week_template(cluster_week, avg_sessions, dist_df):
    rows = dist_df[dist_df["cluster_week"] == cluster_week]
    plan = []

    for _, row in rows.iterrows():
        plan += [SESSION_LABELS[row["cluster_session"]]] * round(
            row["pct"] * avg_sessions
        )

    while len(plan) < avg_sessions:
        plan.append("easy")
    while len(plan) > avg_sessions:
        plan.pop()

    return plan


def _adjust_plan_by_risk(plan, avg_risk):
    if avg_risk > 0.75:
        return ["easy" if s == "intensity" else s for s in plan]
    if avg_risk < 0.30 and "intensity" not in plan:
        plan[-1] = "intensity"
    return plan


def _adjust_with_done_sessions(plan, done_types, remaining_sessions):
    print("\n🛠️ DEBUG _adjust_with_done_sessions")
    print("Plan initial :", plan)
    print("Séances déjà faites :", done_types)
    print("Nombre de séances restantes :", remaining_sessions)

    plan_copy = plan.copy()

    for done in done_types:
        if done in plan_copy:
            print(f"➡️ Suppression de : {done}")
            plan_copy.remove(done)
        else:
            print(f"⚠️ {done} non trouvé dans le plan")

    adjusted = plan_copy[:remaining_sessions]

    while len(adjusted) < remaining_sessions:
        adjusted.append("easy")

    print("Plan final ajusté :", adjusted)
    return adjusted


def enrich_plan_with_descriptions(plan: list[str]) -> list[dict]:
    """
    Convert a list of session types into rich session recommendations.
    """
    enriched = []

    for session_type in plan:
        # desc = SESSION_DESCRIPTIONS.get(session_type)
        profile = SESSION_PROFILES.get(session_type)

        if profile is None:
            continue

        enriched.append(
            {
                "type": session_type,
                "label": profile["label"],
                # "objective": profile["objective"],
                # "description": profile["description"],
                # "physiology": profile["physiology"],
                "data_profile": profile["data_profile"],
            }
        )

    return enriched
