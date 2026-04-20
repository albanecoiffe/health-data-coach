import pandas as pd
import plotly.express as px
import streamlit as st

from db import load_all_sessions, resolve_user_id


st.set_page_config(page_title="Analyse Totale", layout="wide")
st.title("Running - Total depuis le debut")


@st.cache_data(ttl=60)
def load_data(user_id):
    return load_all_sessions(user_id)


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

zones = pd.DataFrame(
    {
        "zone": ["Z1", "Z2", "Z3", "Z4", "Z5"],
        "minutes": [dt[f"z{i}_min"].sum() for i in range(1, 6)],
    }
)
fig_zones = px.bar(
    zones,
    x="zone",
    y="minutes",
    title="Temps par zone cardiaque",
    labels={"zone": "Zone", "minutes": "Minutes"},
    color="zone",
    color_discrete_map={
        "Z1": "#2ecc71",
        "Z2": "#2f80ed",
        "Z3": "#f2c94c",
        "Z4": "#f2994a",
        "Z5": "#eb5757",
    },
)
st.plotly_chart(fig_zones, width="stretch")
