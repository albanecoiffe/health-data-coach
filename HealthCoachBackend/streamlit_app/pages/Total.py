import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from db import load_all_sessions, resolve_user_id
from core.heart_rate_zones import HEART_RATE_ZONES, zone_color_map, zone_ranges_rows


st.set_page_config(page_title="Analyse Totale", layout="wide")
st.title("Running - Total depuis le debut")

HR_SENSOR_START = pd.Timestamp("2025-09-14")


@st.cache_data(ttl=60)
def load_data(user_id):
    return load_all_sessions(user_id)


def format_pace(minutes_per_km: float) -> str:
    if pd.isna(minutes_per_km) or minutes_per_km <= 0:
        return "-"
    total_seconds = int(round(minutes_per_km * 60))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02d}/km"


def zone_columns_for_ids(zone_ids: tuple[str, ...]) -> list[str]:
    return [zone.column for zone in HEART_RATE_ZONES if zone.id in zone_ids]


def prepare_footing_sessions(
    df: pd.DataFrame,
    easy_threshold: float,
    low_zone_ids: tuple[str, ...],
) -> pd.DataFrame:
    sessions = df.copy()
    all_zone_columns = [zone.column for zone in HEART_RATE_ZONES]
    low_zone_columns = zone_columns_for_ids(low_zone_ids)
    sessions["zone_total_min"] = sessions[all_zone_columns].sum(axis=1)
    sessions["selected_low_zone_min"] = sessions[low_zone_columns].sum(axis=1)
    sessions["selected_low_intensity_pct"] = (
        sessions["selected_low_zone_min"]
        .div(sessions["zone_total_min"].replace(0, pd.NA))
        .fillna(0.0)
    )
    sessions["has_hr"] = sessions["avg_hr"] > 0
    sessions["meters_per_min"] = (
        (sessions["distance_km"] * 1000)
        .div(sessions["duration_min"].replace(0, pd.NA))
        .fillna(0.0)
    )
    sessions["efficiency_score"] = (
        sessions["meters_per_min"].div(sessions["avg_hr"].replace(0, pd.NA)).fillna(0.0)
    )

    long_enough = sessions["duration_min"] >= 20
    far_enough = sessions["distance_km"] >= 3
    easy_enough = (
        (sessions["zone_total_min"] <= 0)
        | (sessions["selected_low_intensity_pct"] >= easy_threshold)
    )

    return sessions.loc[long_enough & far_enough & easy_enough].copy()


def compare_blocks(df: pd.DataFrame, size: int) -> dict[str, float]:
    block = min(size, len(df) // 2)
    if block == 0:
        return {}

    first = df.head(block)
    last = df.tail(block)
    return {
        "block_size": block,
        "avg_hr_delta": last["avg_hr"].mean() - first["avg_hr"].mean(),
        "pace_delta": last["pace_min_per_km"].mean() - first["pace_min_per_km"].mean(),
        "efficiency_delta": last["efficiency_score"].mean()
        - first["efficiency_score"].mean(),
    }


def add_linear_trend(
    fig,
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    name: str,
    color: str,
):
    trend = df[[x_col, y_col]].dropna().sort_values(x_col)
    if len(trend) < 2:
        return

    x_num = trend[x_col].astype("int64")
    slope, intercept = np.polyfit(x_num, trend[y_col], 1)
    fig.add_scatter(
        x=trend[x_col],
        y=(slope * x_num) + intercept,
        mode="lines",
        name=name,
        line=dict(color=color, width=2, dash="dot"),
    )


def style_legend(fig):
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            title_text="",
        ),
        coloraxis_colorbar=dict(title="", len=0.75),
    )


def render_footing_analysis(
    source_df: pd.DataFrame,
    low_zone_ids: tuple[str, ...],
    low_zone_label: str,
    key_prefix: str,
):
    st.markdown(f"### Footings filtres avec {low_zone_label}")
    st.caption(
        "Regle utilisee: footing >= 20 min, >= 3 km, et part du temps cardiaque dans "
        f"{low_zone_label} au-dessus du seuil choisi."
    )

    c_easy, c_band = st.columns(2)
    easy_threshold_pct = c_easy.slider(
        "Part minimale en basse intensite pour classer un footing",
        min_value=50,
        max_value=100,
        value=100,
        step=5,
        format="%d%%",
        key=f"{key_prefix}_easy_threshold",
    )
    easy_threshold = easy_threshold_pct / 100
    comparison_band_sec = c_band.slider(
        "Tolerance pour comparer des seances proches en FC",
        min_value=10,
        max_value=60,
        value=20,
        step=5,
        key=f"{key_prefix}_comparison_band_sec",
    )

    target_pace_min, target_pace_max = st.slider(
        "Plage d'allure pour analyser la FC",
        min_value=5.0,
        max_value=8.5,
        value=(6.75, 7.25),
        step=5 / 60,
        format="%.2f min/km",
        key=f"{key_prefix}_target_pace_range",
    )

    footings = prepare_footing_sessions(
        source_df, easy_threshold, low_zone_ids
    ).sort_values("start_time")
    footings_hr = footings.loc[footings["has_hr"]].copy()

    with st.expander(f"Definitions {low_zone_label}", expanded=False):
        st.markdown(
            f"""
            - `Z1` a `Z5` sont tes zones cardiaques affichees plus haut dans la page.
            - Ici, la "basse intensite" veut dire `{low_zone_label}`.
            - `100 %` signifie que toute la seance doit etre dans `{low_zone_label}`.
            - `80 %` signifie qu'au moins 80 % du temps en zones cardiaques doit etre dans `{low_zone_label}`.
            """
        )

    if footings.empty:
        st.info(
            f"Aucun footing detecte depuis le 14/09/2025 avec la definition {low_zone_label} "
            "et les filtres actuels."
        )
        return

    if footings_hr.empty:
        st.info(
            "Des footings ont ete detectes, mais aucune frequence cardiaque moyenne exploitable n'est disponible."
        )
        return

    footings_hr["pace_label"] = footings_hr["pace_min_per_km"].apply(format_pace)
    footings_hr["avg_hr_rolling"] = footings_hr["avg_hr"].rolling(5, min_periods=2).mean()
    footings_hr["pace_rolling"] = (
        footings_hr["pace_min_per_km"].rolling(5, min_periods=2).mean()
    )
    footings_hr["efficiency_rolling"] = (
        footings_hr["efficiency_score"].rolling(5, min_periods=2).mean()
    )

    summary = compare_blocks(footings_hr, size=5)
    first_last_cols = st.columns(4)
    first_last_cols[0].metric("Footings detectes", len(footings))
    first_last_cols[1].metric("Footings avec cardio", len(footings_hr))
    first_last_cols[2].metric(
        "FC moyenne footing",
        f"{footings_hr['avg_hr'].mean():.0f} bpm",
        None
        if not summary
        else f"{summary['avg_hr_delta']:+.1f} bpm vs {int(summary['block_size'])} premiers",
        delta_color="inverse",
    )
    first_last_cols[3].metric(
        "Allure moyenne footing",
        format_pace(footings_hr["pace_min_per_km"].mean()),
        None
        if not summary
        else f"{summary['pace_delta'] * 60:+.0f} sec/km vs {int(summary['block_size'])} premiers",
        delta_color="inverse",
    )

    fig_hr_trend = px.scatter(
        footings_hr,
        x="start_time",
        y="avg_hr",
        color="pace_min_per_km",
        color_continuous_scale="Blues",
        title=f"1. Frequence cardiaque moyenne sur les footings ({low_zone_label})",
        labels={
            "start_time": "Date",
            "avg_hr": "FC moyenne (bpm)",
            "pace_min_per_km": "Allure",
        },
        hover_data={"pace_label": True, "distance_km": ":.1f", "duration_min": ":.0f"},
    )
    fig_hr_trend.add_scatter(
        x=footings_hr["start_time"],
        y=footings_hr["avg_hr_rolling"],
        mode="lines",
        name="Moyenne mobile",
        line=dict(color="#eb5757", width=3),
    )
    add_linear_trend(
        fig_hr_trend, footings_hr, "start_time", "avg_hr", "Tendance", "#eb5757"
    )
    style_legend(fig_hr_trend)
    st.plotly_chart(fig_hr_trend, width="stretch")

    fig_pace_trend = px.scatter(
        footings_hr,
        x="start_time",
        y="pace_min_per_km",
        color="avg_hr",
        color_continuous_scale="Viridis",
        title=f"2. Allure des footings dans le temps ({low_zone_label})",
        labels={
            "start_time": "Date",
            "pace_min_per_km": "Allure (min/km)",
            "avg_hr": "FC moyenne",
        },
        hover_data={"pace_label": True, "distance_km": ":.1f", "duration_min": ":.0f"},
    )
    fig_pace_trend.add_scatter(
        x=footings_hr["start_time"],
        y=footings_hr["pace_rolling"],
        mode="lines",
        name="Moyenne mobile",
        line=dict(color="#2f80ed", width=3),
    )
    add_linear_trend(
        fig_pace_trend,
        footings_hr,
        "start_time",
        "pace_min_per_km",
        "Tendance",
        "#2f80ed",
    )
    style_legend(fig_pace_trend)
    fig_pace_trend.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_pace_trend, width="stretch")

    same_pace = footings_hr.loc[
        footings_hr["pace_min_per_km"].between(target_pace_min, target_pace_max)
    ].copy()

    median_hr = float(footings_hr["avg_hr"].median())
    hr_band = max(3, round(comparison_band_sec / 5))
    same_hr = footings_hr.loc[
        footings_hr["avg_hr"].between(median_hr - hr_band, median_hr + hr_band)
    ].copy()

    comp_a, comp_b = st.columns(2)

    if len(same_pace) >= 3:
        fig_same_pace = px.scatter(
            same_pace,
            x="start_time",
            y="avg_hr",
            title=(
                f"3. FC pour les footings entre {format_pace(target_pace_min)} "
                f"et {format_pace(target_pace_max)} ({low_zone_label})"
            ),
            labels={"start_time": "Date", "avg_hr": "FC moyenne (bpm)"},
            hover_data={
                "pace_label": True,
                "distance_km": ":.1f",
                "duration_min": ":.0f",
            },
        )
        add_linear_trend(
            fig_same_pace,
            same_pace,
            "start_time",
            "avg_hr",
            "Tendance",
            "#eb5757",
        )
        style_legend(fig_same_pace)
        comp_a.plotly_chart(fig_same_pace, width="stretch")
    else:
        comp_a.info("Pas assez de footings dans cette plage d'allure pour comparer la FC.")

    if len(same_hr) >= 3:
        fig_same_hr = px.scatter(
            same_hr,
            x="start_time",
            y="pace_min_per_km",
            title=f"4. Allure a FC comparable autour de {median_hr:.0f} bpm ({low_zone_label})",
            labels={"start_time": "Date", "pace_min_per_km": "Allure (min/km)"},
            hover_data={
                "pace_label": True,
                "distance_km": ":.1f",
                "duration_min": ":.0f",
            },
        )
        add_linear_trend(
            fig_same_hr,
            same_hr,
            "start_time",
            "pace_min_per_km",
            "Tendance",
            "#2f80ed",
        )
        style_legend(fig_same_hr)
        fig_same_hr.update_yaxes(autorange="reversed")
        comp_b.plotly_chart(fig_same_hr, width="stretch")
    else:
        comp_b.info("Pas assez de footings proches en FC pour comparer l'allure.")

    fig_efficiency = px.line(
        footings_hr,
        x="start_time",
        y="efficiency_score",
        markers=True,
        title=f"5. Efficacite cardio sur les footings ({low_zone_label})",
        labels={
            "start_time": "Date",
            "efficiency_score": "Metres/minute par bpm",
        },
        hover_data={"pace_label": True, "avg_hr": ":.0f", "distance_km": ":.1f"},
    )
    fig_efficiency.add_scatter(
        x=footings_hr["start_time"],
        y=footings_hr["efficiency_rolling"],
        mode="lines",
        name="Moyenne mobile",
        line=dict(color="#27ae60", width=3),
    )
    style_legend(fig_efficiency)
    st.plotly_chart(fig_efficiency, width="stretch")

    latest_insight = (
        "Lecture rapide: une baisse de FC a allure comparable, ou une allure plus rapide a FC comparable, "
        "suggere une amelioration de ton cardio sur les footings."
    )
    if summary:
        latest_insight += (
            f" Sur les {int(summary['block_size'])} derniers footings compares aux {int(summary['block_size'])} premiers, "
            f"ta FC evolue de {summary['avg_hr_delta']:+.1f} bpm, ton allure de {summary['pace_delta'] * 60:+.0f} sec/km "
            f"et ton score d'efficacite de {summary['efficiency_delta']:+.3f}."
        )
    st.info(latest_insight)


user_id = resolve_user_id()
df = load_data(user_id)
st.caption(f"Source: Neon ou CSV local - user_id={user_id or 'non defini'}")

if df.empty:
    st.info("Aucune seance en base.")
    st.stop()

min_date = df["start_time"].min().date()
max_date = df["start_time"].max().date()
c0, c1 = st.columns(2)
start = c0.date_input("Debut", min_date)
end = c1.date_input("Fin", max_date)

if start > end:
    st.error("La date de debut doit etre <= date de fin.")
    st.stop()

mask = (df["start_time"].dt.date >= start) & (df["start_time"].dt.date <= end)
dt = df.loc[mask].copy()

if dt.empty:
    st.info("Aucune seance sur cette periode.")
    st.stop()

dt["week_start"] = dt["start_time"].dt.to_period("W").apply(lambda p: p.start_time)
dt["month"] = dt["start_time"].dt.to_period("M").apply(lambda p: p.start_time)

weekly = dt.groupby("week_start", as_index=False).agg(
    distance_km=("distance_km", "sum"),
    duration_min=("duration_min", "sum"),
)
monthly = dt.groupby("month", as_index=False).agg(distance_km=("distance_km", "sum"))

total_distance = dt["distance_km"].sum()
total_duration = dt["duration_min"].sum()
total_sessions = len(dt)
avg_weekly = weekly["distance_km"].mean()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Distance", f"{total_distance:.1f} km")
m2.metric("Duree", f"{total_duration:.0f} min")
m3.metric("Seances", total_sessions)
m4.metric("Moyenne hebdo", f"{avg_weekly:.1f} km")

st.divider()
fig_weekly = px.line(
    weekly,
    x="week_start",
    y="distance_km",
    markers=True,
    title="Distance totale courue par semaine",
    labels={"week_start": "Semaine", "distance_km": "Distance (km)"},
)
fig_weekly.update_traces(line=dict(color="#2f80ed", width=3), marker=dict(size=7))
st.plotly_chart(fig_weekly, width="stretch")

fig_monthly = px.bar(
    monthly,
    x="month",
    y="distance_km",
    title="Distance totale par mois",
    labels={"month": "Mois", "distance_km": "Distance (km)"},
)
fig_monthly.update_traces(marker_color="#2f80ed")
st.plotly_chart(fig_monthly, width="stretch")

st.subheader("Zones cardiaques")
st.dataframe(pd.DataFrame(zone_ranges_rows()), width="stretch", hide_index=True)

zones = pd.DataFrame(
    {
        "zone": [zone.label for zone in HEART_RATE_ZONES],
        "minutes": [dt[zone.column].sum() for zone in HEART_RATE_ZONES],
    }
)
fig_zones = px.bar(
    zones,
    x="zone",
    y="minutes",
    title="Temps par zone cardiaque",
    labels={"zone": "Zone", "minutes": "Minutes"},
    color="zone",
    color_discrete_map=zone_color_map(),
)
st.plotly_chart(fig_zones, width="stretch")

st.divider()
st.subheader("Analyse cardio sur les footings")
st.caption(
    "Les footings sont detectes automatiquement comme des seances d'au moins 20 min et 3 km. "
    "La definition de basse intensite est precisee dans chaque bloc. "
    "Cette analyse ne prend en compte que les seances depuis le 14/09/2025, date de debut du capteur cardiaque."
)

dt_hr = dt.loc[dt["start_time"] >= HR_SENSOR_START].copy()
if dt_hr.empty:
    st.info(
        "Aucune seance a partir du 14/09/2025 dans la plage selectionnee. "
        "Les visualisations cardio des footings commencent a cette date."
    )
    st.stop()

with st.expander("Analyses proposees", expanded=False):
    st.markdown(
        """
        - Evolution de la frequence cardiaque moyenne sur tes footings.
        - Evolution de l'allure sur tes footings.
        - Frequence cardiaque a allure comparable.
        - Allure a frequence cardiaque comparable.
        - Score d'efficacite cardio: metres/minute par bpm.
        - Meme analyse en definition large `Z1 + Z2 + Z3`, puis en definition stricte `Z1 + Z2`.
        """
    )

render_footing_analysis(dt_hr, ("z1", "z2", "z3"), "Z1 + Z2 + Z3", "z123")
st.divider()
render_footing_analysis(dt_hr, ("z1", "z2"), "Z1 + Z2", "z12")
