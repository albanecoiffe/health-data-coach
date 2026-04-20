from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from db import load_sessions_between, resolve_user_id


st.set_page_config(page_title="Analyse Semaine", layout="wide")
st.title("Course - Semaine")


def get_week_range(week_offset: int):
    today = datetime.today()
    start = today - timedelta(days=today.weekday())
    start += timedelta(weeks=week_offset)
    end = start + timedelta(days=7)
    return start.date(), end.date()


@st.cache_data(ttl=60)
def load_week_sessions(user_id: str, start_date, end_date):
    return load_sessions_between(user_id, start_date, end_date)


if "week_offset" not in st.session_state:
    st.session_state.week_offset = 0

user_id = resolve_user_id()
st.caption(f"Source: Neon (run_sessions) - user_id={user_id}")

col_prev, col_label, col_next = st.columns([1, 3, 1])
with col_prev:
    if st.button("⬅️"):
        st.session_state.week_offset -= 1
with col_next:
    if st.button("➡️") and st.session_state.week_offset < 0:
        st.session_state.week_offset += 1

start_date, end_date = get_week_range(st.session_state.week_offset)
col_label.markdown(
    f"<h3 style='text-align:center;'>Semaine du {start_date} au {end_date - timedelta(days=1)}</h3>",
    unsafe_allow_html=True,
)

df = load_week_sessions(user_id, start_date, end_date)
df_prev = load_week_sessions(
    user_id,
    start_date - timedelta(days=7),
    end_date - timedelta(days=7),
)

if df.empty:
    st.info("Aucune seance cette semaine.")
    st.stop()

total_distance = df["distance_km"].sum()
total_duration = df["duration_min"].sum()
total_elevation = df["elevation_m"].sum()
session_count = len(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Distance", f"{total_distance:.1f} km")
c2.metric("Duree", f"{total_duration:.0f} min")
c3.metric("Denivele", f"{total_elevation:.0f} m")
c4.metric("Seances", f"{session_count}")

st.divider()

df_chart = df.copy()
df_chart["day_label"] = df_chart["start_time"].dt.strftime("%a %d")

fig_distance = px.bar(
    df_chart,
    x="day_label",
    y="distance_km",
    hover_data=["duration_min", "pace_min_per_km", "avg_hr"],
    title="Distance par seance",
    template="plotly_dark",
)
st.plotly_chart(fig_distance, use_container_width=True)

zones_totals = pd.DataFrame(
    {
        "zone": ["Z1", "Z2", "Z3", "Z4", "Z5"],
        "minutes": [
            df["z1_min"].sum(),
            df["z2_min"].sum(),
            df["z3_min"].sum(),
            df["z4_min"].sum(),
            df["z5_min"].sum(),
        ],
    }
)

fig_zones = px.bar(
    zones_totals,
    x="zone",
    y="minutes",
    title="Zones cardiaques (temps total semaine)",
    color="zone",
    color_discrete_map={
        "Z1": "#2ecc71",
        "Z2": "#3498db",
        "Z3": "#f1c40f",
        "Z4": "#e67e22",
        "Z5": "#e74c3c",
    },
    template="plotly_dark",
)
st.plotly_chart(fig_zones, use_container_width=True)

zones_ref = pd.DataFrame(
    {
        "Zone": ["Z1", "Z2", "Z3", "Z4", "Z5"],
        "Plage BPM": ["< 145", "145 - 158", "159 - 172", "173 - 185", ">= 186"],
    }
)
st.caption("Correspondance des zones cardiaques (meme seuils que l'app iOS)")
st.dataframe(zones_ref, use_container_width=True, hide_index=True)

low_avg = df["low_intensity_pct"].mean() * 100
high_avg = df["high_intensity_pct"].mean() * 100
c5, c6 = st.columns(2)
c5.metric("Low intensity (Z1-Z3)", f"{low_avg:.0f} %")
c6.metric("High intensity (Z4-Z5)", f"{high_avg:.0f} %")

st.divider()
st.subheader("Compare a la semaine precedente")

prev_distance = df_prev["distance_km"].sum() if not df_prev.empty else 0
prev_duration = df_prev["duration_min"].sum() if not df_prev.empty else 0
prev_elevation = df_prev["elevation_m"].sum() if not df_prev.empty else 0
prev_sessions = len(df_prev) if not df_prev.empty else 0

c7, c8, c9, c10 = st.columns(4)
c7.metric("Delta distance", f"{total_distance - prev_distance:+.1f} km")
c8.metric("Delta duree", f"{total_duration - prev_duration:+.1f} min")
c9.metric("Delta denivele", f"{total_elevation - prev_elevation:+.1f} m")
c10.metric("Delta seances", f"{session_count - prev_sessions:+d}")

with st.expander("Details des seances"):
    st.dataframe(
        df[
            [
                "start_time",
                "distance_km",
                "duration_min",
                "avg_hr",
                "elevation_m",
                "pace_min_per_km",
                "z1_min",
                "z2_min",
                "z3_min",
                "z4_min",
                "z5_min",
            ]
        ],
        use_container_width=True,
    )
