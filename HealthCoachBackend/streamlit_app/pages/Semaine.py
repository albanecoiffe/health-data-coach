from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import load_sessions_between, resolve_user_id


st.set_page_config(page_title="Analyse Semaine", layout="wide")
st.title("Course - Semaine")


def get_week_range(offset: int):
    today = date.today()
    start = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return start, start + timedelta(days=7)


@st.cache_data(ttl=60)
def load_week_sessions(user_id, start_date, end_date):
    return load_sessions_between(user_id, start_date, end_date)


def week_distance_by_day(df, start_date):
    days = pd.date_range(start_date, periods=7, freq="D")
    daily = (
        df.assign(day=df["start_time"].dt.normalize())
        .groupby("day", as_index=False)
        .agg(distance_km=("distance_km", "sum"))
    )
    daily = pd.DataFrame({"day": days}).merge(daily, on="day", how="left").fillna(0)
    daily["day_label"] = daily["day"].dt.strftime("%a %d/%m")
    return daily


def zone_breakdown_by_session(df):
    sessions = df.sort_values("start_time").copy()
    sessions["session_label"] = sessions["start_time"].dt.strftime("%a %d/%m %H:%M")
    return sessions.melt(
        id_vars=["session_label"],
        value_vars=[f"z{i}_min" for i in range(1, 6)],
        var_name="zone",
        value_name="minutes",
    ).replace(
        {
            "z1_min": "Z1",
            "z2_min": "Z2",
            "z3_min": "Z3",
            "z4_min": "Z4",
            "z5_min": "Z5",
        }
    )


if "week_offset" not in st.session_state:
    st.session_state.week_offset = 0

user_id = resolve_user_id()
st.caption(f"Source: Neon ou CSV local - user_id={user_id or 'non defini'}")

col_prev, col_label, col_next = st.columns([1, 3, 1])
if col_prev.button("<"):
    st.session_state.week_offset -= 1
if col_next.button(">"):
    st.session_state.week_offset += 1

start_date, end_date = get_week_range(st.session_state.week_offset)
col_label.markdown(
    f"<h3 style='text-align:center;'>Semaine du {start_date} au {end_date - timedelta(days=1)}</h3>",
    unsafe_allow_html=True,
)

df = load_week_sessions(user_id, start_date, end_date)
df_prev = load_week_sessions(user_id, start_date - timedelta(days=7), start_date)

if df.empty:
    st.info("Aucune seance sur cette semaine.")
    st.stop()

total_distance = df["distance_km"].sum()
total_duration = df["duration_min"].sum()
total_elevation = df["elevation_m"].sum()
session_count = len(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Distance", f"{total_distance:.1f} km")
c2.metric("Duree", f"{total_duration:.0f} min")
c3.metric("Denivele", f"{total_elevation:.0f} m")
c4.metric("Seances", session_count)

st.divider()
daily = week_distance_by_day(df, start_date)
fig_distance = px.bar(
    daily,
    x="day_label",
    y="distance_km",
    title="Distance courue par jour",
    labels={"day_label": "Jour", "distance_km": "Distance (km)"},
)
fig_distance.update_traces(marker_color="#2f80ed")
st.plotly_chart(fig_distance, width="stretch")

zones = zone_breakdown_by_session(df)
fig_zones = px.bar(
    zones,
    x="session_label",
    y="minutes",
    color="zone",
    title="Zones cardiaques (min par seance)",
    labels={"session_label": "Seance", "minutes": "Minutes", "zone": "Zone"},
    color_discrete_map={
        "Z1": "#2ecc71",
        "Z2": "#2f80ed",
        "Z3": "#f2c94c",
        "Z4": "#f2994a",
        "Z5": "#eb5757",
    },
)
fig_zones.update_layout(barmode="stack")
st.plotly_chart(fig_zones, width="stretch")

delta_data = pd.DataFrame(
    {
        "metric": ["Distance", "Temps total", "Denivele", "Seances"],
        "delta": [
            total_distance
            - (df_prev["distance_km"].sum() if not df_prev.empty else 0.0),
            total_duration
            - (df_prev["duration_min"].sum() if not df_prev.empty else 0.0),
            total_elevation
            - (df_prev["elevation_m"].sum() if not df_prev.empty else 0.0),
            session_count - (len(df_prev) if not df_prev.empty else 0),
        ],
    }
)
fig_delta = go.Figure(
    go.Bar(
        x=delta_data["metric"],
        y=delta_data["delta"],
        marker_color=[
            "#27ae60" if value >= 0 else "#eb5757" for value in delta_data["delta"]
        ],
    )
)
fig_delta.update_layout(title="Compare a la semaine derniere", yaxis_title="Delta")
st.plotly_chart(fig_delta, width="stretch")

previous_distance = df_prev["distance_km"].sum() if not df_prev.empty else 0.0
st.write(f"Semaine precedente: {previous_distance:.1f} km")
