from services.periods import format_period_for_display


def factual_response(snapshot, metric: str) -> dict:
    start, end = format_period_for_display(snapshot.period.start, snapshot.period.end)

    # DEBUG
    print("DEBUG snapshot.totals =", snapshot.totals.dict())

    # Aucune séance
    if snapshot.totals.sessions == 0:
        return {
            "reply": f"Aucune séance enregistrée sur la période du {start} au {end}."
        }

    metric = metric.upper()

    # -------------------
    # DISTANCE
    # -------------------
    if metric == "DISTANCE":
        return {
            "reply": (
                f"Sur la période du {start} au {end}, "
                f"tu as couru {round(snapshot.totals.distance_km, 1)} km."
            )
        }

    # -------------------
    # DURÉE
    # -------------------
    if metric == "DURATION":
        minutes = round(snapshot.totals.duration_min)
        hours = minutes // 60
        mins = minutes % 60

        if hours > 0:
            return {
                "reply": (
                    f"Sur la période du {start} au {end}, "
                    f"tu as couru pendant {hours}h{mins:02d}."
                )
            }
        else:
            return {
                "reply": (
                    f"Sur la période du {start} au {end}, "
                    f"tu as couru pendant {minutes} minutes."
                )
            }

    # -------------------
    # SÉANCES
    # -------------------
    if metric == "SESSIONS":
        return {
            "reply": (
                f"Sur la période du {start} au {end}, "
                f"tu as effectué {snapshot.totals.sessions} séances."
            )
        }

    # -------------------
    # DÉNIVELÉ
    # -------------------
    if metric == "ELEVATION":
        return {
            "reply": (
                f"Sur la période du {start} au {end}, "
                f"tu as accumulé {round(snapshot.totals.elevation_m)} m de dénivelé positif."
            )
        }

    # -------------------
    # FRÉQUENCE CARDIAQUE MOYENNE
    # -------------------
    if metric == "AVG_HR":
        if snapshot.totals.avg_hr is None:
            return {
                "reply": (
                    f"Aucune donnée de fréquence cardiaque disponible "
                    f"sur la période du {start} au {end}."
                )
            }

        return {
            "reply": (
                f"Sur la période du {start} au {end}, "
                f"ta fréquence cardiaque moyenne était de "
                f"{round(snapshot.totals.avg_hr)} bpm pendant tes courses."
            )
        }

    # -------------------
    # LOAD (redirigé proprement)
    # -------------------
    if metric == "LOAD":
        if snapshot.training_load is None:
            return {
                "reply": (
                    f"La charge d’entraînement n’est pas disponible "
                    f"sur la période du {start} au {end}."
                )
            }

        return {
            "reply": (
                f"Sur la période du {start} au {end}, "
                f"ta charge d’entraînement était de "
                f"{round(snapshot.training_load.load_7d, 1)}."
            )
        }

    # -------------------
    # FALLBACK PROPRE
    # -------------------
    return {
        "reply": (
            f"Sur la période du {start} au {end}, "
            f"tu as effectué {snapshot.totals.sessions} séances "
            f"pour {round(snapshot.totals.distance_km, 1)} km."
        )
    }
