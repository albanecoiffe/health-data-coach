from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from db import load_sessions_between, resolve_user_id


st.set_page_config(page_title="Analyse Annee", layout="wide")
st.title("Course - Annee")

user_id = resolve_user_id()
current_year = date.today().year
year = st.number_input(
    "Annee", min_value=2020, max_value=current_year, value=current_year
)

start_date = date(int(year), 1, 1)
end_date = date(int(year) + 1, 1, 1)
df = load_sessions_between(user_id, start_date, end_date)

st.caption(f"Source: Neon (run_sessions) - user_id={user_id}")

if df.empty:
    st.info("Aucune seance sur cette annee.")
    st.stop()

df["month"] = df["start_time"].dt.month
df["month_label"] = df["start_time"].dt.strftime("%b")
df["week_start"] = df["start_time"].dt.to_period("W").apply(lambda p: p.start_time)

monthly = (
    df.groupby(["month", "month_label"], as_index=False)
    .agg(
        distance_km=("distance_km", "sum"),
        duration_min=("duration_min", "sum"),
        elevation_m=("elevation_m", "sum"),
        sessions=("start_time", "count"),
    )
    .sort_values("month")
)

weekly = (
    df.groupby("week_start", as_index=False)
    .agg(distance_km=("distance_km", "sum"))
    .sort_values("week_start")
)

total_distance = df["distance_km"].sum()
total_duration = df["duration_min"].sum()
total_elevation = df["elevation_m"].sum()
total_sessions = len(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Distance annee", f"{total_distance:.0f} km")
c2.metric("Duree annee", f"{total_duration:.0f} min")
c3.metric("Denivele annee", f"{total_elevation:.0f} m")
c4.metric("Seances annee", f"{total_sessions}")

st.divider()

fig_month = px.bar(
    monthly,
    x="month_label",
    y="distance_km",
    title="Distance totale par mois",
    hover_data=["duration_min", "sessions", "elevation_m"],
    template="plotly_dark",
)
st.plotly_chart(fig_month, use_container_width=True)

fig_week = px.line(
    weekly,
    x="week_start",
    y="distance_km",
    markers=True,
    title="Distance totale courue par semaine",
    template="plotly_dark",
)
st.plotly_chart(fig_week, use_container_width=True)

best_month = monthly.sort_values("distance_km", ascending=False).iloc[0]
st.subheader("Meilleur mois")
st.write(
    f"{best_month['month_label']} {year} - {best_month['distance_km']:.1f} km, "
    f"{int(best_month['sessions'])} seances"
)
