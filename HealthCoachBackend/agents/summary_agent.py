from services.periods import format_period_for_display


def summary_response(snapshot) -> dict:
    start, end = format_period_for_display(snapshot.period.start, snapshot.period.end)

    if snapshot.totals.sessions == 0:
        return {
            "reply": f"Aucune séance enregistrée sur la période du {start} au {end}."
        }

    distance = round(snapshot.totals.distance_km, 1)
    duration_min = round(snapshot.totals.duration_min)
    hours = duration_min // 60
    minutes = duration_min % 60
    sessions = snapshot.totals.sessions
    elevation = round(snapshot.totals.elevation_m)

    # ❤️ Répartition cardiaque détaillée (EXISTANT — inchangé)
    zones_text = []
    zones = getattr(snapshot, "zones_percent", None)

    if isinstance(zones, dict) and zones:
        for z in ["z1", "z2", "z3", "z4", "z5"]:
            val = zones.get(z)
            if isinstance(val, (int, float)) and val > 0:
                zones_text.append(f"{z.upper()} : {round(val * 100)}%")

    zones_str = ", ".join(zones_text) if zones_text else "non disponibles"

    # 🔥 / 🟢 Intensité (AJOUT)
    if isinstance(zones, dict) and zones:
        low_intensity = zones.get("z1", 0) + zones.get("z2", 0) + zones.get("z3", 0)
        high_intensity = zones.get("z4", 0) + zones.get("z5", 0)

        if low_intensity + high_intensity > 0:
            low_str = f"{round(low_intensity * 100)}%"
            high_str = f"{round(high_intensity * 100)}%"
        else:
            low_str = "non disponibles"
            high_str = "non disponibles"
    else:
        low_str = "non disponibles"
        high_str = "non disponibles"

    # 🏅 Plus longue sortie
    longest = getattr(snapshot, "longest_run_km", None)
    longest_str = (
        f"{round(longest, 1)} km"
        if isinstance(longest, (int, float)) and longest > 0
        else "non disponible"
    )

    return {
        "reply": (
            f"📊 Bilan de la période {start} → {end}\n\n"
            f"🏃 Distance totale : {distance} km\n"
            f"⏱️ Temps total : {hours}h{minutes:02d}\n"
            f"📆 Séances : {sessions}\n"
            f"⛰️ D+ : {elevation} m\n\n"
            f"❤️ Répartition cardiaque : {zones_str}\n"
            f"🔥 Haute intensité (Z4–Z5) : {high_str}\n"
            f"🟢 Basse intensité (Z1–Z3) : {low_str}\n\n"
            f"🏅 Plus longue sortie : {longest_str}"
        )
    }
