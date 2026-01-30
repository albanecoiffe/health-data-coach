from to_delete.periods import format_period_for_display
from datetime import date
from sqlalchemy.orm import Session
from uuid import UUID

from to_delete.periods import format_period_for_display
from metrics.aggregates import get_aggregated_totals


def factual_response(db, user_id, start, end, metric: str) -> str:
    start_str, end_str = format_period_for_display(start.isoformat(), end.isoformat())

    metric = metric.upper()

    # ======================================================
    # 📊 Récupération agrégats DB
    # ======================================================
    totals = get_aggregated_totals(db, user_id, start, end)
    totals = get_aggregated_totals(
        db=db,
        user_id=user_id,
        start=start,
        end=end,
    )

    if totals["sessions"] == 0:
        return f"Aucune séance enregistrée sur la période du {start_str} au {end_str}."

    # ======================================================
    # DISTANCE
    # ======================================================
    if metric == "DISTANCE":
        return (
            f"Sur la période du {start_str} au {end_str}, "
            f"tu as couru {round(totals['distance_km'], 1)} km."
        )

    # ======================================================
    # DURÉE
    # ======================================================
    if metric == "DURATION":
        minutes = round(totals["duration_min"])
        hours = minutes // 60
        mins = minutes % 60

        if hours > 0:
            return (
                f"Sur la période du {start_str} au {end_str}, "
                f"tu as couru pendant {hours}h{mins:02d}."
            )
        else:
            return (
                f"Sur la période du {start_str} au {end_str}, "
                f"tu as couru pendant {minutes} minutes."
            )

    # ======================================================
    # SÉANCES
    # ======================================================
    if metric == "SESSIONS":
        return (
            f"Sur la période du {start_str} au {end_str}, "
            f"tu as effectué {totals['sessions']} séances."
        )

    # ======================================================
    # DÉNIVELÉ
    # ======================================================
    if metric == "ELEVATION":
        return (
            f"Sur la période du {start_str} au {end_str}, "
            f"tu as accumulé {round(totals['elevation_m'])} m de dénivelé positif."
        )

    # ======================================================
    # FRÉQUENCE CARDIAQUE
    # ======================================================
    if metric == "AVG_HR":
        if totals["avg_hr"] is None:
            return (
                f"Aucune donnée de fréquence cardiaque disponible "
                f"sur la période du {start_str} au {end_str}."
            )

        return (
            f"Sur la période du {start_str} au {end_str}, "
            f"ta fréquence cardiaque moyenne était de "
            f"{round(totals['avg_hr'])} bpm."
        )

    # ======================================================
    # FALLBACK PROPRE
    # ======================================================
    return (
        f"Sur la période du {start_str} au {end_str}, "
        f"tu as effectué {totals['sessions']} séances "
        f"pour {round(totals['distance_km'], 1)} km."
    )
