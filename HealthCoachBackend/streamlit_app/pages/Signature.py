from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.services.signature.analysis import (
    SIGNATURE_METRIC_DEFINITIONS,
    SignatureMetricDefinition,
    build_runner_signature_from_dataframe,
)
from db import load_all_sessions, resolve_user_id


st.set_page_config(page_title="Signature du coureur", layout="wide")
st.title("Signature du coureur")


@st.cache_data(ttl=60)
def load_signature_context(user_id: str | None):
    sessions = load_all_sessions(user_id)
    if sessions.empty:
        return pd.DataFrame(), {}, pd.DataFrame()

    signature, weekly = build_runner_signature_from_dataframe(sessions)
    return sessions, signature.model_dump(by_alias=True), weekly


def nested_value(payload: dict, dotted_key: str):
    current = payload
    for part in dotted_key.split("."):
        current = current[part]
    return current


def format_value(value, value_format: str) -> str:
    if value_format == "km_1":
        return f"{value:.1f} km"
    if value_format == "min_0":
        return f"{value:.0f} min"
    if value_format == "count_1":
        return f"{value:.1f}"
    if value_format == "count_0":
        return f"{int(round(value))}"
    if value_format == "days_0":
        return f"{int(round(value))} j"
    if value_format == "weeks_0":
        return f"{int(round(value))} sem"
    if value_format == "ratio_pct_0":
        return f"{value * 100:.0f} %"
    if value_format == "pct_signed_1":
        return f"{value:+.1f} %"
    if value_format == "ratio_2":
        return f"{value:.2f}"
    if value_format == "load_0":
        return f"{value:.0f}"
    return str(value)


def format_date_fr(value) -> str:
    return pd.to_datetime(value).strftime("%d/%m/%Y")


def period_days(start_value, end_value) -> int:
    start_dt = pd.to_datetime(start_value)
    end_dt = pd.to_datetime(end_value)
    return int((end_dt - start_dt).days) + 1


def window_label(window_df: pd.DataFrame) -> str:
    start_value = window_df["week_start"].iloc[0]
    end_value = window_df["week_start"].iloc[-1] + pd.Timedelta(days=6)
    days = period_days(start_value, end_value)
    return f"{format_date_fr(start_value)} -> {format_date_fr(end_value)} ({days} j)"


def _frame_active(weekly: pd.DataFrame, column: str) -> pd.DataFrame:
    return weekly.loc[weekly["had_run"], ["week_start", column]].reset_index(drop=True)


def _frame_all_weeks(weekly: pd.DataFrame, column: str) -> pd.DataFrame:
    return weekly.loc[:, ["week_start", column]].reset_index(drop=True)


def _frame_acwr(weekly: pd.DataFrame) -> pd.DataFrame:
    return weekly.loc[weekly["acwr"] > 0, ["week_start", "acwr"]].reset_index(drop=True)


def _split_windows(frame: pd.DataFrame, window: int) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    if len(frame) < window * 2:
        return None
    recent = frame.iloc[-window:].reset_index(drop=True)
    previous = frame.iloc[-2 * window : -window].reset_index(drop=True)
    return recent, previous


def _delta_text(current: float, previous: float, value_format: str, label: str) -> str | None:
    delta = current - previous
    if value_format == "km_1":
        return f"{delta:+.1f} km vs {label}"
    if value_format == "min_0":
        return f"{delta:+.0f} min vs {label}"
    if value_format == "count_1":
        return f"{delta:+.1f} vs {label}"
    if value_format == "count_0":
        return f"{delta:+.0f} vs {label}"
    if value_format == "days_0":
        return f"{delta:+.0f} j vs {label}"
    if value_format == "weeks_0":
        return f"{delta:+.0f} sem vs {label}"
    if value_format == "ratio_pct_0":
        return f"{delta * 100:+.0f} pts vs {label}"
    if value_format == "pct_signed_1":
        return f"{delta:+.1f} pts vs {label}"
    if value_format == "ratio_2":
        return f"{delta:+.2f} vs {label}"
    if value_format == "load_0":
        return f"{delta:+.0f} vs {label}"
    return None


def _pct_variation(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def _comparison_payload(
    current: float,
    previous: float,
    value_format: str,
    label: str,
    recent_label: str,
    previous_label: str,
) -> dict[str, str | float | None]:
    return {
        "recent": format_value(current, value_format),
        "precedent": format_value(previous, value_format),
        "variation_pct": _pct_variation(current, previous),
        "label": label,
        "recent_label": recent_label,
        "previous_label": previous_label,
        "current_raw": current,
        "previous_raw": previous,
    }


def _build_comparison(
    frame: pd.DataFrame,
    value_column: str,
    window: int,
    reducer: str,
    value_format: str,
    label: str,
) -> dict[str, str | float | None] | None:
    windows = _split_windows(frame, window)
    if not windows:
        return None

    recent, previous = windows
    if reducer == "mean":
        current = float(recent[value_column].mean())
        previous_value = float(previous[value_column].mean())
    elif reducer == "std":
        current = float(recent[value_column].std(ddof=0))
        previous_value = float(previous[value_column].std(ddof=0))
    elif reducer == "max":
        current = float(recent[value_column].max())
        previous_value = float(previous[value_column].max())
    else:
        return None

    return _comparison_payload(
        current,
        previous_value,
        value_format,
        label,
        window_label(recent),
        window_label(previous),
    )


def metric_comparison(
    definition: SignatureMetricDefinition,
    weekly: pd.DataFrame,
) -> dict[str, str | float | None] | None:
    label_12w = "12 sem recentes vs 12 sem precedentes"
    label_8w = "8 sem recentes vs 8 sem precedentes"

    if definition.key == "volume.weekly_avg_km":
        return _build_comparison(_frame_active(weekly, "distance_km"), "distance_km", 12, "mean", definition.value_format, label_12w)
    if definition.key == "volume.weekly_std_km":
        return _build_comparison(_frame_active(weekly, "distance_km"), "distance_km", 12, "std", definition.value_format, label_12w)
    if definition.key == "duration.weekly_avg_min":
        return _build_comparison(_frame_active(weekly, "duration_min"), "duration_min", 12, "mean", definition.value_format, label_12w)
    if definition.key == "duration.weekly_std_min":
        return _build_comparison(_frame_active(weekly, "duration_min"), "duration_min", 12, "std", definition.value_format, label_12w)
    if definition.key == "frequency.weekly_avg_sessions":
        return _build_comparison(_frame_active(weekly, "sessions_count"), "sessions_count", 12, "mean", definition.value_format, label_12w)
    if definition.key == "frequency.weekly_std_sessions":
        return _build_comparison(_frame_active(weekly, "sessions_count"), "sessions_count", 12, "std", definition.value_format, label_12w)
    if definition.key == "intensity.z4_z5_avg_pct":
        return _build_comparison(_frame_active(weekly, "high_intensity_pct"), "high_intensity_pct", 12, "mean", definition.value_format, label_12w)
    if definition.key == "intensity.z1_z3_avg_pct":
        return _build_comparison(_frame_active(weekly, "low_intensity_pct"), "low_intensity_pct", 12, "mean", definition.value_format, label_12w)
    if definition.key == "load.weekly_avg_load":
        return _build_comparison(_frame_active(weekly, "weekly_load"), "weekly_load", 12, "mean", definition.value_format, label_12w)
    if definition.key == "load.weekly_std_load":
        return _build_comparison(_frame_active(weekly, "weekly_load"), "weekly_load", 12, "std", definition.value_format, label_12w)
    if definition.key == "load.acwr_avg":
        return _build_comparison(_frame_acwr(weekly), "acwr", 8, "mean", definition.value_format, label_8w)
    if definition.key == "load.acwr_max":
        return _build_comparison(_frame_acwr(weekly), "acwr", 8, "max", definition.value_format, label_8w)
    if definition.key == "regularity.weeks_with_runs_pct":
        frame = _frame_all_weeks(weekly.assign(had_run_float=weekly["had_run"].astype(float)), "had_run_float")
        return _build_comparison(frame, "had_run_float", 12, "mean", definition.value_format, label_12w)
    if definition.key == "regularity.longest_break_days":
        return _build_comparison(_frame_all_weeks(weekly, "break_streak_days"), "break_streak_days", 12, "max", definition.value_format, label_12w)
    if definition.key == "robustness.injury_free_weeks_pct":
        frame = _frame_all_weeks(weekly.assign(had_run_float=weekly["had_run"].astype(float)), "had_run_float")
        return _build_comparison(frame, "had_run_float", 12, "mean", definition.value_format, label_12w)
    if definition.key == "robustness.max_consecutive_weeks":
        return _build_comparison(_frame_all_weeks(weekly, "active_streak_weeks"), "active_streak_weeks", 12, "max", definition.value_format, label_12w)
    return None


def metric_delta(definition: SignatureMetricDefinition, weekly: pd.DataFrame) -> str | None:
    comparison = metric_comparison(definition, weekly)
    if comparison:
        return _delta_text(
            float(comparison["current_raw"]),
            float(comparison["previous_raw"]),
            definition.value_format,
            str(comparison["label"]).split(" vs ")[-1],
        )
    if definition.key == "volume.trend_12w_pct":
        return f"{nested_value(signature_payload, definition.key):+.1f} % recent"
    if definition.key == "intensity.z4_z5_trend_12w_pct":
        return f"{nested_value(signature_payload, definition.key):+.1f} % recent"
    if definition.key == "robustness.breaks_over7d_count":
        return None
    if definition.key == "adaptation.load_std_trend12w_pct":
        return f"{nested_value(signature_payload, definition.key):+.1f} % recent"
    return None


def render_evolution_block(
    definitions: list[SignatureMetricDefinition],
    weekly: pd.DataFrame,
) -> None:
    rows = []
    period_label = None
    for definition in definitions:
        comparison = metric_comparison(definition, weekly)
        if not comparison:
            continue
        period_label = str(comparison["label"])
        variation = comparison["variation_pct"]
        rows.append(
            {
                "Metrique": definition.label,
                "Recent": f"{comparison['recent']} | {comparison['recent_label']}",
                "Precedent": f"{comparison['precedent']} | {comparison['previous_label']}",
                "Variation": "-" if variation is None else f"{variation:+.1f} %",
            }
        )

    if not rows:
        st.caption("Pas assez d'historique pour afficher une comparaison recente fiable sur cette section.")
        return

    if period_label:
        st.caption(f"Evolution recente: {period_label}")
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def render_definition_table(definitions: list[SignatureMetricDefinition]) -> None:
    rows = [
        {
            "Metrique": definition.label,
            "Definition": definition.description,
            "Lecture": definition.interpretation,
        }
        for definition in definitions
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def render_overview_card(title: str, value: str, subtitle: str | None = None) -> None:
    subtitle_html = (
        f"<div style='margin-top:0.9rem;font-size:0.92rem;color:#8f96a3;line-height:1.45;'>{subtitle}</div>"
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div style="
            padding:1.05rem 1.15rem 1rem 1.15rem;
            border:1px solid rgba(250,250,250,0.10);
            border-radius:1rem;
            min-height:180px;
            background:linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.015));
            display:flex;
            flex-direction:column;
            justify-content:space-between;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
        ">
            <div style="font-size:0.95rem;color:#b3b8c4;margin-bottom:0.85rem;font-weight:600;">{title}</div>
            <div style="font-size:1.75rem;font-weight:700;line-height:1.18;letter-spacing:-0.02em;">{value}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def base_layout(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


def chart_volume(weekly: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=weekly["week_start"],
        y=weekly["distance_km"],
        name="Distance hebdo",
        marker_color="#2d9cdb",
    )
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["distance_rolling_4w"],
        name="Moyenne mobile 4 sem",
        mode="lines",
        line=dict(color="#1b4965", width=3),
    )
    fig.update_layout(title="Evolution du volume hebdomadaire")
    fig.update_yaxes(title_text="km")
    return base_layout(fig)


def chart_duration(weekly: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=weekly["week_start"],
        y=weekly["duration_min"],
        name="Duree hebdo",
        marker_color="#27ae60",
    )
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["duration_rolling_4w"],
        name="Moyenne mobile 4 sem",
        mode="lines",
        line=dict(color="#1e8449", width=3),
    )
    fig.update_layout(title="Evolution du temps d'entrainement hebdomadaire")
    fig.update_yaxes(title_text="minutes")
    return base_layout(fig)


def chart_frequency(weekly: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(
        x=weekly["week_start"],
        y=weekly["sessions_count"],
        name="Seances hebdo",
        marker_color="#9b51e0",
    )
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["sessions_rolling_4w"],
        name="Moyenne mobile 4 sem",
        mode="lines",
        line=dict(color="#6c3483", width=3),
    )
    fig.update_layout(title="Evolution du nombre de seances")
    fig.update_yaxes(title_text="seances")
    return base_layout(fig)


def chart_intensity(weekly: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["low_intensity_pct"] * 100,
        name="Z1-Z3",
        mode="lines+markers",
        line=dict(color="#2d9cdb", width=3),
    )
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["high_intensity_pct"] * 100,
        name="Z4-Z5",
        mode="lines+markers",
        line=dict(color="#eb5757", width=3),
    )
    fig.update_layout(title="Evolution de la repartition d'intensite")
    fig.update_yaxes(title_text="% de la duree hebdo", rangemode="tozero")
    return base_layout(fig)


def chart_load(weekly: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(
        x=weekly["week_start"],
        y=weekly["weekly_load"],
        name="Charge hebdo",
        marker_color="#f2994a",
        secondary_y=False,
    )
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["load_rolling_4w"],
        name="Charge moyenne 4 sem",
        mode="lines",
        line=dict(color="#8d5524", width=3),
        secondary_y=False,
    )
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["acwr"],
        name="ACWR",
        mode="lines",
        line=dict(color="#2f80ed", width=3, dash="dot"),
        secondary_y=True,
    )
    fig.update_layout(title="Evolution de la charge et de l'ACWR")
    fig.update_yaxes(title_text="charge", secondary_y=False)
    fig.update_yaxes(title_text="ratio ACWR", secondary_y=True)
    return base_layout(fig)


def chart_regularity(weekly: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(
        x=weekly["week_start"],
        y=weekly["had_run"].astype(int),
        name="Semaine active",
        marker_color="#27ae60",
        secondary_y=False,
    )
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["active_weeks_rolling_4w"] * 100,
        name="Regularite 4 sem",
        mode="lines",
        line=dict(color="#1b4965", width=3),
        secondary_y=True,
    )
    fig.update_layout(title="Semaines actives et regularite recente")
    fig.update_yaxes(title_text="0 ou 1", secondary_y=False)
    fig.update_yaxes(title_text="% sur 4 sem", secondary_y=True, range=[0, 100])
    return base_layout(fig)


def chart_robustness(weekly: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["active_streak_weeks"],
        name="Serie active",
        mode="lines+markers",
        line=dict(color="#27ae60", width=3),
        secondary_y=False,
    )
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["break_streak_days"],
        name="Coupure en cours",
        mode="lines+markers",
        line=dict(color="#eb5757", width=3),
        secondary_y=True,
    )
    fig.update_layout(title="Series actives et coupures")
    fig.update_yaxes(title_text="semaines actives consecutives", secondary_y=False)
    fig.update_yaxes(title_text="jours sans course", secondary_y=True)
    return base_layout(fig)


def chart_adaptation(weekly: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["load_std_rolling_4w"],
        name="Variabilite de charge 4 sem",
        mode="lines+markers",
        line=dict(color="#6c5ce7", width=3),
        secondary_y=False,
    )
    fig.add_scatter(
        x=weekly["week_start"],
        y=weekly["weekly_load"],
        name="Charge hebdo",
        mode="lines",
        line=dict(color="#bdbdbd", width=2, dash="dot"),
        secondary_y=True,
    )
    fig.update_layout(title="Adaptation: variabilite de charge")
    fig.update_yaxes(title_text="ecart-type glissant", secondary_y=False)
    fig.update_yaxes(title_text="charge hebdo", secondary_y=True)
    return base_layout(fig)


CHARTS_BY_CATEGORY = {
    "Volume": chart_volume,
    "Duree": chart_duration,
    "Frequence": chart_frequency,
    "Intensite": chart_intensity,
    "Charge": chart_load,
    "Regularite": chart_regularity,
    "Robustesse": chart_robustness,
    "Adaptation": chart_adaptation,
}


def render_metrics(
    signature_payload: dict,
    definitions: list[SignatureMetricDefinition],
    weekly: pd.DataFrame,
) -> None:
    columns = st.columns(min(4, max(1, len(definitions))))
    for idx, definition in enumerate(definitions):
        columns[idx % len(columns)].metric(
            definition.label,
            format_value(nested_value(signature_payload, definition.key), definition.value_format),
            metric_delta(definition, weekly),
        )


user_id = resolve_user_id()
sessions_df, signature_payload, weekly_df = load_signature_context(user_id)

st.caption(f"Source: sessions Neon ou CSV local - user_id={user_id or 'non defini'}")

if sessions_df.empty or not signature_payload:
    st.info("Aucune donnee disponible pour construire la signature du coureur.")
    st.stop()

window_start = pd.to_datetime(signature_payload["period"]["start"]).date()
window_end = pd.to_datetime(signature_payload["period"]["end"]).date()
window_sessions = sessions_df.loc[
    (sessions_df["start_time"] >= pd.Timestamp(window_start))
    & (sessions_df["start_time"] <= pd.Timestamp(window_end))
].copy()

overview = st.columns(3)
with overview[0]:
    render_overview_card(
        "Periode analysee",
        f"{format_date_fr(window_start)}<br><span style='font-size:1.2rem;font-weight:600;color:#c8ccd4;'>au</span> {format_date_fr(window_end)}",
        f"{period_days(window_start, window_end)} jours analyses",
    )
with overview[1]:
    render_overview_card(
        "Seances dans la fenetre",
        str(len(window_sessions)),
        "Toutes les seances retenues dans la signature",
    )
with overview[2]:
    render_overview_card(
        "Semaines actives",
        str(int(weekly_df["had_run"].sum())),
        f"sur {len(weekly_df)} semaines completes",
    )

st.caption(
    "La signature est calculee a la volee depuis les sessions. "
    "La semaine ISO en cours est exclue des tendances pour eviter de biaiser les comparaisons."
)

with st.expander("Comment lire cette page", expanded=False):
    st.markdown(
        """
        - La signature decrit ton profil d'entrainement long terme sur une fenetre glissante de 52 semaines.
        - Les cartes donnent la valeur de synthese de chaque metrique.
        - Quand c'est possible, le delta compare la periode recente a une periode precedente equivalente.
        - Les graphiques montrent l'evolution hebdomadaire qui explique cette valeur.
        - Les moyennes et ecarts-types de volume, duree, frequence et charge sont calcules sur les semaines actives.
        """
    )

categories = []
for metric_definition in SIGNATURE_METRIC_DEFINITIONS:
    if metric_definition.category not in categories:
        categories.append(metric_definition.category)

tabs = st.tabs(categories)

for tab, category in zip(tabs, categories):
    definitions = [
        definition
        for definition in SIGNATURE_METRIC_DEFINITIONS
        if definition.category == category
    ]
    with tab:
        st.caption(
            "Comparaison recente affichee dans les deltas: bloc recent vs bloc precedent comparable."
        )
        render_evolution_block(definitions, weekly_df)
        render_metrics(signature_payload, definitions, weekly_df)
        st.plotly_chart(CHARTS_BY_CATEGORY[category](weekly_df), width="stretch")
        with st.expander(f"Definitions des metriques {category}", expanded=False):
            render_definition_table(definitions)
