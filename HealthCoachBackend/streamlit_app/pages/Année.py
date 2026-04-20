import calendar
from datetime import date

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import load_sessions_between, resolve_user_id


st.set_page_config(page_title="Analyse Annee", layout="wide")
st.title("Course - Annee")

MONTH_NAMES = [
    "Janvier",
    "Fevrier",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Aout",
    "Septembre",
    "Octobre",
    "Novembre",
    "Decembre",
]


def build_month_heatmap(df, year, month):
    month_days = calendar.monthrange(year, month)[1]
    first_day = date(year, month, 1)
    offset = first_day.weekday()
    rows = (month_days + offset + 6) // 7

    daily = (
        df.assign(day=df["start_time"].dt.date)
        .groupby("day", as_index=False)
        .agg(distance_km=("distance_km", "sum"))
    )
    distance_by_day = dict(zip(daily["day"], daily["distance_km"]))

    z = [[None for _ in range(7)] for _ in range(rows)]
    text = [["" for _ in range(7)] for _ in range(rows)]
    custom = [["" for _ in range(7)] for _ in range(rows)]

    for day in range(1, month_days + 1):
        current = date(year, month, day)
        index = offset + day - 1
        row = index // 7
        col = index % 7
        distance = float(distance_by_day.get(current, 0.0))
        z[row][col] = distance
        text[row][col] = str(day)
        custom[row][col] = f"{day:02d}/{month:02d}/{year}: {distance:.1f} km"

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
            y=[f"S{i + 1}" for i in range(rows)],
            text=text,
            texttemplate="%{text}",
            customdata=custom,
            hovertemplate="%{customdata}<extra></extra>",
            colorscale=[
                [0.00, "rgba(90, 90, 90, 0.22)"],
                [0.01, "rgba(47, 128, 237, 0.30)"],
                [0.25, "rgba(47, 128, 237, 0.55)"],
                [0.50, "rgba(39, 174, 96, 0.75)"],
                [1.00, "rgba(39, 174, 96, 1.00)"],
            ],
            zmin=0,
            zmax=max(20, df["distance_km"].max() if not df.empty else 20),
            showscale=False,
            xgap=8,
            ygap=8,
        )
    )
    fig.update_yaxes(autorange="reversed", showgrid=False, visible=False)
    fig.update_xaxes(side="top", showgrid=False)
    fig.update_layout(
        title="Heatmap - Regularite",
        height=330,
        margin=dict(l=10, r=10, t=60, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


user_id = resolve_user_id()
current_year = date.today().year
year = int(
    st.number_input("Annee", min_value=2020, max_value=current_year, value=current_year)
)

start_date = date(year, 1, 1)
end_date = date(year + 1, 1, 1)
df = load_sessions_between(user_id, start_date, end_date)
st.caption(f"Source: Neon ou CSV local - user_id={user_id or 'non defini'}")

if df.empty:
    st.info("Aucune seance sur cette annee.")
    st.stop()

df["month"] = df["start_time"].dt.to_period("M").apply(lambda p: p.start_time)
df["month_label"] = df["month"].dt.strftime("%b")
df["week_start"] = df["start_time"].dt.to_period("W").apply(lambda p: p.start_time)
df["week_number"] = df["start_time"].dt.isocalendar().week.astype(int)

monthly = df.groupby(["month", "month_label"], as_index=False).agg(
    distance_km=("distance_km", "sum"),
    duration_min=("duration_min", "sum"),
)
weekly = (
    df.groupby("week_number", as_index=False)
    .agg(distance_km=("distance_km", "sum"))
    .set_index("week_number")
    .reindex(range(1, 53), fill_value=0)
    .rename_axis("week_number")
    .reset_index()
)

total_distance = df["distance_km"].sum()
total_duration = df["duration_min"].sum()
total_elevation = df["elevation_m"].sum()
total_sessions = len(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Distance", f"{total_distance:.1f} km")
c2.metric("Duree", f"{total_duration:.0f} min")
c3.metric("Denivele", f"{total_elevation:.0f} m")
c4.metric("Seances", total_sessions)

st.divider()
fig_month = px.bar(
    monthly,
    x="month_label",
    y="distance_km",
    title="Distance totale par mois",
    labels={"month_label": "Mois", "distance_km": "Distance (km)"},
)
fig_month.update_traces(marker_color="#2f80ed")
st.plotly_chart(fig_month, width="stretch")

best_month = monthly.sort_values("distance_km", ascending=False).iloc[0]
st.subheader("Meilleur mois")
st.write(f"{best_month['month_label']}: {best_month['distance_km']:.1f} km")

month_options = {
    MONTH_NAMES[i - 1]: i
    for i in range(1, 13)
    if not df[df["start_time"].dt.month == i].empty or i == date.today().month
}
selected_month_name = st.selectbox(
    "Mois pour la heatmap",
    list(month_options.keys()),
    index=(
        list(month_options.values()).index(date.today().month)
        if date.today().month in month_options.values()
        else 0
    ),
)
selected_month = month_options[selected_month_name]
st.plotly_chart(build_month_heatmap(df, year, selected_month), width="stretch")

month_total = df[df["start_time"].dt.month == selected_month]["distance_km"].sum()
st.write(f"Total {selected_month_name}: {month_total:.1f} km")

fig_week = px.line(
    weekly,
    x="week_number",
    y="distance_km",
    markers=True,
    title="Distance totale courue par semaine",
    labels={"week_number": "Semaine", "distance_km": "Distance (km)"},
)
fig_week.update_traces(line=dict(color="#2f80ed", width=3), marker=dict(size=7))
fig_week.update_xaxes(tickmode="array", tickvals=list(range(0, 53, 4)))
st.plotly_chart(fig_week, width="stretch")
