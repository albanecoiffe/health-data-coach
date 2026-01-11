from services.periods import format_period_for_display


def factual_response(snapshot, metric: str) -> dict:
    start, end = format_period_for_display(snapshot.period.start, snapshot.period.end)

    # Aucune séance
    if snapshot.totals.sessions == 0:
        return {
            "reply": f"Aucune séance enregistrée sur la période du {start} au {end}."
        }

    metric = metric.upper()

    if metric == "DISTANCE":
        return {
            "reply": (
                f"Sur la période du {start} au {end}, "
                f"tu as couru {round(snapshot.totals.distance_km, 1)} km."
            )
        }

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

    if metric == "SESSIONS":
        return {
            "reply": (
                f"Sur la période du {start} au {end}, "
                f"tu as effectué {snapshot.totals.sessions} séances."
            )
        }

    # Fallback propre
    return {
        "reply": (
            f"Sur la période du {start} au {end}, "
            f"tu as {snapshot.totals.sessions} séances pour "
            f"{round(snapshot.totals.distance_km, 1)} km."
        )
    }
