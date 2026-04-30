from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from db import load_all_sessions, resolve_user_id


st.set_page_config(page_title="Classification des seances", layout="wide")
st.title("Classification des seances")

HR_SENSOR_START = pd.Timestamp("2025-09-14")

NOTEBOOK_RESULTS = {
    "baseline_macro_f1": 0.862,
    "baseline_bal_acc": 0.854,
    "enriched_macro_f1": 0.949,
    "enriched_bal_acc": 0.937,
}


@st.cache_data(ttl=60)
def load_data(user_id: str | None) -> pd.DataFrame:
    return load_all_sessions(user_id)


def format_pace(minutes_per_km: float) -> str:
    if pd.isna(minutes_per_km) or minutes_per_km <= 0:
        return "—"
    total_seconds = int(round(minutes_per_km * 60))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}/km"


user_id = resolve_user_id()
df = load_data(user_id)
st.caption(f"Source: Neon ou CSV local - user_id={user_id or 'non defini'}")

if df.empty:
    st.info("Aucune seance disponible.")
    st.stop()

study_df = df.loc[df["start_time"] >= HR_SENSOR_START].copy()
labeled_df = study_df.loc[study_df["session_type"].notna()].copy()
unlabeled_df = study_df.loc[study_df["session_type"].isna()].copy()

tab_overview, tab_study, tab_prod, tab_live = st.tabs(
    [
        "Vue d'ensemble",
        "Etude notebook",
        "Prod actuelle",
        "Predictions live",
    ]
)

with tab_overview:
    st.subheader("Pourquoi on fait cette classification")
    st.markdown(
        """
        L'objectif n'est pas juste de stocker des seances. L'objectif est de distinguer automatiquement :

        - les `footing`
        - les `fractionné`
        - les `sortie longue`
        - et, plus tard, des cas plus rares comme `semi marathon` ou `marathon`

        Cette couche est utile pour :

        - mieux lire l'historique d'entrainement
        - faire des stats par type de seance
        - alimenter plus tard du clustering, de la recommandation et de l'analyse de structure
        - pre-remplir l'app pour que le coureur confirme au lieu de tout saisir a la main
        """
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Seances etudiees", len(study_df))
    c2.metric("Seances labelisees", len(labeled_df))
    c3.metric("Seances sans label", len(unlabeled_df))
    c4.metric("Types valides", labeled_df["session_type"].nunique() if not labeled_df.empty else 0)

    counts = (
        study_df["effective_session_type"]
        .fillna("non classee")
        .value_counts()
        .rename_axis("type")
        .reset_index(name="count")
    )
    fig = px.bar(
        counts,
        x="type",
        y="count",
        color="type",
        title="Repartition actuelle des types de seance",
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")


with tab_study:
    st.subheader("Ce qu'on a fait dans le notebook")
    st.markdown(
        """
        Dans le notebook, on a mene deux types de travail :

        - exploration de la similarite entre seances
        - classification supervisee des types de seance

        Concretement :

        - embedding tabulaire construit a partir de distance, duree, allure, FC moyenne, kcal, denivele et temps en zones
        - projection 2D avec PCA pour voir si les seances se regroupent naturellement
        - clustering KMeans pour observer des groupes interpretable
        - classification avec une `LogisticRegression`
        - puis enrichissement avec des features derivees de `session_detail`
        """
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Macro F1 baseline", f"{NOTEBOOK_RESULTS['baseline_macro_f1']:.3f}")
    m2.metric("Balanced acc baseline", f"{NOTEBOOK_RESULTS['baseline_bal_acc']:.3f}")
    m3.metric("Macro F1 enrichi", f"{NOTEBOOK_RESULTS['enriched_macro_f1']:.3f}")
    m4.metric("Balanced acc enrichi", f"{NOTEBOOK_RESULTS['enriched_bal_acc']:.3f}")

    progress = pd.DataFrame(
        {
            "modele": ["Baseline", "Baseline + session_detail"],
            "Macro F1": [
                NOTEBOOK_RESULTS["baseline_macro_f1"],
                NOTEBOOK_RESULTS["enriched_macro_f1"],
            ],
            "Balanced accuracy": [
                NOTEBOOK_RESULTS["baseline_bal_acc"],
                NOTEBOOK_RESULTS["enriched_bal_acc"],
            ],
        }
    ).melt(id_vars="modele", var_name="metric", value_name="score")

    fig = px.bar(
        progress,
        x="metric",
        y="score",
        color="modele",
        barmode="group",
        text="score",
        title="Resultats obtenus dans le notebook",
        range_y=[0, 1],
    )
    fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    st.plotly_chart(fig, width="stretch")

    st.markdown(
        """
        ### Ce qu'on a appris

        - les signaux physiologiques seuls marchent deja bien pour distinguer les grandes categories
        - la structure du `session_detail` apporte un vrai gain pour separer `fractionné` et `sortie longue`
        - les classes rares comme `semi marathon` et `marathon` sont encore trop peu nombreuses pour une evaluation stable
        - certaines seances pourraient etre mieux traitees au niveau "vraie seance" consolidee plutot qu'au niveau segment
        """
    )

    st.markdown(
        """
        ### Ce qu'on n'a pas encore industrialise

        - pas de modele sauvegarde en `.joblib` pour cette classification
        - pas de pipeline de training offline / inference online
        - pas de consolidation automatique des segments appartenant a une meme seance
        - pas de prediction automatique du `session_detail`
        """
    )


with tab_prod:
    st.subheader("Ce qui tourne aujourd'hui en production locale")
    st.markdown(
        """
        La prod actuelle est volontairement plus simple que le notebook.

        Quand une seance n'a pas encore de `session_type` valide :

        - le backend recupere les seances deja labelisees du meme coureur
        - il entraine a la volee une `LogisticRegression`
        - il predit une `predicted_session_type`
        - l'app iPhone et Streamlit affichent cette prediction
        - le coureur peut confirmer ou corriger
        - la valeur validee est ensuite stockee en base

        Si le backend n'a pas assez de labels pour entrainer correctement, il tombe sur une heuristique simple :

        - gros volume => `sortie longue`
        - forte intensite => `fractionné`
        - sinon => `footing`
        """
    )

    st.info(
        "Important: la prod actuelle n'utilise pas encore les features enrichies derivees de `session_detail` pour la prediction initiale."
    )

    recent = (
        study_df.sort_values("start_time", ascending=False)
        .head(12)[
            [
                "start_time",
                "distance_km",
                "duration_min",
                "pace_min_per_km",
                "session_type",
                "predicted_session_type",
                "effective_session_type",
                "session_detail",
            ]
        ]
        .copy()
    )
    recent["start_time"] = recent["start_time"].dt.strftime("%Y-%m-%d %H:%M")
    recent["pace_min_per_km"] = recent["pace_min_per_km"].apply(format_pace)
    st.dataframe(recent, width="stretch", hide_index=True)


with tab_live:
    st.subheader("A quoi ressemblent les predictions live")
    live_df = study_df.sort_values("start_time", ascending=False).copy()
    live_df["start_label"] = live_df["start_time"].dt.strftime("%a %d/%m %H:%M")
    live_df["pace_label"] = live_df["pace_min_per_km"].apply(format_pace)
    live_df["status"] = live_df["session_type"].apply(
        lambda value: "validee" if isinstance(value, str) and value.strip() else "a confirmer"
    )

    c1, c2 = st.columns([1.3, 1])
    with c1:
        focus = st.radio(
            "Filtre",
            ["Toutes", "Seulement a confirmer", "Seulement validees"],
            horizontal=True,
        )
    with c2:
        horizon_days = st.slider("Fenetre recente (jours)", 7, 240, 60, 7)

    min_date = pd.Timestamp.today() - timedelta(days=horizon_days)
    live_df = live_df.loc[live_df["start_time"] >= min_date]

    if focus == "Seulement a confirmer":
        live_df = live_df.loc[live_df["status"] == "a confirmer"]
    elif focus == "Seulement validees":
        live_df = live_df.loc[live_df["status"] == "validee"]

    if live_df.empty:
        st.info("Aucune seance dans ce filtre.")
    else:
        scatter = px.scatter(
            live_df,
            x="distance_km",
            y="duration_min",
            color="effective_session_type",
            symbol="status",
            hover_data=[
                "start_label",
                "pace_label",
                "avg_hr",
                "session_type",
                "predicted_session_type",
                "session_detail",
            ],
            title="Vue live des seances et de leur type",
            labels={
                "distance_km": "Distance (km)",
                "duration_min": "Duree (min)",
                "effective_session_type": "Type",
            },
        )
        st.plotly_chart(scatter, width="stretch")

        preview = live_df[
            [
                "start_label",
                "distance_km",
                "duration_min",
                "pace_label",
                "avg_hr",
                "session_type",
                "predicted_session_type",
                "effective_session_type",
                "session_detail",
                "status",
            ]
        ].rename(
            columns={
                "start_label": "seance",
                "distance_km": "distance_km",
                "duration_min": "duree_min",
                "pace_label": "allure",
                "avg_hr": "fc_moy",
                "session_type": "label_valide",
                "predicted_session_type": "prediction",
                "effective_session_type": "type_affiche",
                "session_detail": "detail",
            }
        )
        st.dataframe(preview, width="stretch", hide_index=True)
