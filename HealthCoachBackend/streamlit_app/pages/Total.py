from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from db import load_all_sessions, resolve_user_id


st.set_page_config(page_title="Analyse Totale", layout="wide")
st.title("Running - Total depuis le debut")


@st.cache_data(ttl=60)
def load_data(user_id: str) -> pd.DataFrame:
    return load_all_sessions(user_id)


user_id = resolve_user_id()
df = load_data(user_id)
st.caption(f"Source: Neon (run_sessions) - user_id={user_id}")

if df.empty:
    st.info("Aucune seance en base.")
    st.stop()

min_date = df["start_time"].min().date()
max_date = df["start_time"].max().date()

c0, c1 = st.columns(2)
with c0:
    start = st.date_input("Debut", value=min_date, min_value=min_date, max_value=max_date)
with c1:
    end = st.date_input("Fin", value=max_date, min_value=min_date, max_value=max_date)

if start > end:
    st.error("La date de debut doit etre <= date de fin.")
    st.stop()

mask = (df["start_time"].dt.date >= start) & (df["start_time"].dt.date <= end)
df = df.loc[mask].copy()

if df.empty:
    st.info("Aucune seance sur cette periode.")
    st.stop()

df["week_start"] = df["start_time"].dt.to_period("W").apply(lambda p: p.start_time)
df["month_start"] = df["start_time"].dt.to_period("M").apply(lambda p: p.start_time)
df["year"] = df["start_time"].dt.year

weekly = (
    df.groupby("week_start", as_index=False)
    .agg(
        distance_km=("distance_km", "sum"),
        duration_min=("duration_min", "sum"),
        sessions=("start_time", "count"),
    )
    .sort_values("week_start")
)

monthly = (
    df.groupby("month_start", as_index=False)
    .agg(distance_km=("distance_km", "sum"), duration_min=("duration_min", "sum"))
    .sort_values("month_start")
)

yearly = (
    df.groupby("year", as_index=False)
    .agg(
        distance_km=("distance_km", "sum"),
        duration_min=("duration_min", "sum"),
        sessions=("start_time", "count"),
    )
    .sort_values("year")
)

total_distance = df["distance_km"].sum()
total_duration = df["duration_min"].sum()
total_sessions = len(df)
avg_weekly = weekly["distance_km"].mean() if not weekly.empty else 0.0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Distance totale", f"{total_distance:.0f} km")
m2.metric("Duree totale", f"{total_duration:.0f} min")
m3.metric("Nombre de seances", f"{total_sessions}")
m4.metric("Moyenne km / semaine", f"{avg_weekly:.1f}")

st.divider()

fig_week = px.line(
    weekly,
    x="week_start",
    y="distance_km",
    markers=False,
    title="Distance totale par semaine (toutes annees)",
    template="plotly_dark",
)
st.plotly_chart(fig_week, use_container_width=True)

fig_month = px.line(
    monthly,
    x="month_start",
    y="distance_km",
    title="Distance totale par mois",
    template="plotly_dark",
)
st.plotly_chart(fig_month, use_container_width=True)

fig_year = px.bar(
    yearly,
    x="year",
    y="distance_km",
    hover_data=["duration_min", "sessions"],
    title="Distance totale par annee",
    template="plotly_dark",
)
st.plotly_chart(fig_year, use_container_width=True)

weekly["year"] = weekly["week_start"].dt.year
weekly["week_in_year"] = weekly["week_start"].dt.isocalendar().week.astype(int)
fig_by_year = px.line(
    weekly,
    x="week_in_year",
    y="distance_km",
    color="year",
    title="Profil hebdomadaire compare par annee",
    template="plotly_dark",
)
st.plotly_chart(fig_by_year, use_container_width=True)
