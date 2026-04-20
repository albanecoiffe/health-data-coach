# rag/catalog/registry.py

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class CatalogCase:
    """
    Cas CANONIQUE reconnu par similarité.
    Chaque entrée correspond à UN chemin backend clair.
    """

    text: str  # formulation humaine typique
    use_case: str  # intent backend
    slots: Dict[str, Any]  # slots déjà résolus (PAS de logique ici)


CATALOG_CASES: List[CatalogCase] = [
    # =====================================================
    # 🟦 GET_METRIC — DISTANCE
    # =====================================================
    # --- périodes courantes ---
    CatalogCase(
        text="combien de kilomètres ai-je couru cette semaine",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "this_week"},
    ),
    CatalogCase(
        text="distance totale cette semaine",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "this_week"},
    ),
    CatalogCase(
        text="combien de km ce mois-ci",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "this_month"},
    ),
    CatalogCase(
        text="distance totale le mois dernier",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "last_month"},
    ),
    CatalogCase(
        text="distance parcourue cette année",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "this_year"},
    ),
    # --- périodes glissantes (jours / semaines) ---
    CatalogCase(
        text="distance totale sur les 7 derniers jours",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "last_7_days"},
    ),
    CatalogCase(
        text="combien de kilomètres sur les 14 derniers jours",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "last_14_days"},
    ),
    CatalogCase(
        text="distance sur les 4 dernières semaines",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "last_4_weeks"},
    ),
    # --- périodes glissantes (mois) ---
    CatalogCase(
        text="distance sur les 3 derniers mois",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "last_3_months"},
    ),
    CatalogCase(
        text="distance sur les 6 derniers mois",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "last_6_months"},
    ),
    # --- formulations humaines équivalentes ---
    CatalogCase(
        text="distance parcourue il y a 3 mois",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "last_3_months"},
    ),
    CatalogCase(
        text="distance totale ces dernières semaines",
        use_case="GET_METRIC",
        slots={"metric": "distance_km", "period": "last_4_weeks"},
    ),
    # =====================================================
    # 🟦 GET_METRIC — DURÉE
    # =====================================================
    CatalogCase(
        text="temps total d'entraînement cette semaine",
        use_case="GET_METRIC",
        slots={"metric": "duration_min", "period": "this_week"},
    ),
    CatalogCase(
        text="combien de temps ai-je couru ce mois-ci",
        use_case="GET_METRIC",
        slots={"metric": "duration_min", "period": "this_month"},
    ),
    CatalogCase(
        text="temps total sur les 4 dernières semaines",
        use_case="GET_METRIC",
        slots={"metric": "duration_min", "period": "last_4_weeks"},
    ),
    CatalogCase(
        text="temps d'entraînement sur les 3 derniers mois",
        use_case="GET_METRIC",
        slots={"metric": "duration_min", "period": "last_3_months"},
    ),
    # =====================================================
    # 🟦 GET_METRIC — SÉANCES
    # =====================================================
    CatalogCase(
        text="combien de séances cette semaine",
        use_case="GET_METRIC",
        slots={"metric": "sessions", "period": "this_week"},
    ),
    CatalogCase(
        text="nombre d'entraînements le mois dernier",
        use_case="GET_METRIC",
        slots={"metric": "sessions", "period": "last_month"},
    ),
    CatalogCase(
        text="nombre de séances sur les 4 dernières semaines",
        use_case="GET_METRIC",
        slots={"metric": "sessions", "period": "last_4_weeks"},
    ),
    # =====================================================
    # 🟦 GET_METRIC — FC avg
    # =====================================================
    # --- FRÉQUENCE CARDIAQUE MOYENNE ---
    CatalogCase(
        text="fréquence cardiaque moyenne cette semaine",
        use_case="GET_METRIC",
        slots={"metric": "avg_hr", "period": "this_week"},
    ),
    CatalogCase(
        text="fc moyenne sur les 4 dernières semaines",
        use_case="GET_METRIC",
        slots={"metric": "avg_hr", "period": "last_4_weeks"},
    ),
    CatalogCase(
        text="rythme cardiaque moyen le mois dernier",
        use_case="GET_METRIC",
        slots={"metric": "avg_hr", "period": "last_month"},
    ),
    CatalogCase(
        text="ma fréquence cardiaque moyenne récente",
        use_case="GET_METRIC",
        slots={"metric": "avg_hr", "period": "last_30_days"},
    ),
    # =====================================================
    # 🟦 GET_METRIC — Calories
    # =====================================================
    # --- CALORIES ---
    CatalogCase(
        text="combien de calories ai-je brûlées cette semaine",
        use_case="GET_METRIC",
        slots={"metric": "active_kcal", "period": "this_week"},
    ),
    CatalogCase(
        text="calories dépensées ce mois-ci",
        use_case="GET_METRIC",
        slots={"metric": "active_kcal", "period": "this_month"},
    ),
    CatalogCase(
        text="calories sur les 4 dernières semaines",
        use_case="GET_METRIC",
        slots={"metric": "active_kcal", "period": "last_4_weeks"},
    ),
    CatalogCase(
        text="dépense calorique des 3 derniers mois",
        use_case="GET_METRIC",
        slots={"metric": "active_kcal", "period": "last_3_months"},
    ),
    # =====================================================
    # 🟦 GET_METRIC — ÉLÉVATION
    # =====================================================
    # --- DÉNIVELÉ ---
    CatalogCase(
        text="dénivelé total cette semaine",
        use_case="GET_METRIC",
        slots={"metric": "elevation_m", "period": "this_week"},
    ),
    CatalogCase(
        text="dénivelé cumulé ce mois-ci",
        use_case="GET_METRIC",
        slots={"metric": "elevation_m", "period": "this_month"},
    ),
    CatalogCase(
        text="combien de mètres de dénivelé sur les 4 dernières semaines",
        use_case="GET_METRIC",
        slots={"metric": "elevation_m", "period": "last_4_weeks"},
    ),
    CatalogCase(
        text="dénivelé total des 3 derniers mois",
        use_case="GET_METRIC",
        slots={"metric": "elevation_m", "period": "last_3_months"},
    ),
    # =====================================================
    # 🟦 GET_METRIC — ZONES CARDIAQUES (Z1 → Z5)
    # =====================================================
    # --- ZONES CARDIAQUES ---
    CatalogCase(
        text="temps passé en zone 1 cette semaine",
        use_case="GET_METRIC",
        slots={"metric": "z1_min", "period": "this_week"},
    ),
    CatalogCase(
        text="temps en zone 2 ce mois-ci",
        use_case="GET_METRIC",
        slots={"metric": "z2_min", "period": "this_month"},
    ),
    CatalogCase(
        text="temps passé en zone 3 sur les 4 dernières semaines",
        use_case="GET_METRIC",
        slots={"metric": "z3_min", "period": "last_4_weeks"},
    ),
    CatalogCase(
        text="temps en zone 4 le mois dernier",
        use_case="GET_METRIC",
        slots={"metric": "z4_min", "period": "last_month"},
    ),
    CatalogCase(
        text="temps passé en zone 5 sur les 3 derniers mois",
        use_case="GET_METRIC",
        slots={"metric": "z5_min", "period": "last_3_months"},
    ),
    # =====================================================
    # 🟦 PERIOD_SUMMARY — RÉCAP GLOBAL
    # =====================================================
    CatalogCase(
        text="fais-moi un bilan de la semaine",
        use_case="PERIOD_SUMMARY",
        slots={"period": "this_week"},
    ),
    CatalogCase(
        text="résumé de mes entraînements cette semaine",
        use_case="PERIOD_SUMMARY",
        slots={"period": "this_week"},
    ),
    CatalogCase(
        text="bilan du mois",
        use_case="PERIOD_SUMMARY",
        slots={"period": "this_month"},
    ),
    CatalogCase(
        text="récap de mon activité le mois dernier",
        use_case="PERIOD_SUMMARY",
        slots={"period": "last_month"},
    ),
    CatalogCase(
        text="vue d'ensemble de mes entraînements récents",
        use_case="PERIOD_SUMMARY",
        slots={"period": "last_30_days"},
    ),
    CatalogCase(
        text="bilan des 3 derniers mois",
        use_case="PERIOD_SUMMARY",
        slots={"period": "last_3_months"},
    ),
    # =====================================================
    # 🟦 COMPARE_PERIODS — COMPARAISONS
    # =====================================================
    CatalogCase(
        text="compare cette semaine avec la précédente",
        use_case="COMPARE_PERIODS",
        slots={
            "metric": "distance",
            "period_left": "this_week",
            "period_right": "last_week",
        },
    ),
    CatalogCase(
        text="différence entre cette semaine et la semaine dernière",
        use_case="COMPARE_PERIODS",
        slots={
            "metric": "distance",
            "period_left": "this_week",
            "period_right": "last_week",
        },
    ),
    CatalogCase(
        text="évolution de mon volume entre les deux dernières semaines",
        use_case="COMPARE_PERIODS",
        slots={
            "metric": "distance",
            "period_left": "last_7_days",
            "period_right": "previous_7_days",
        },
    ),
    CatalogCase(
        text="comparaison entre ce mois et le mois dernier",
        use_case="COMPARE_PERIODS",
        slots={
            "metric": "distance",
            "period_left": "this_month",
            "period_right": "last_month",
        },
    ),
    CatalogCase(
        text="est-ce que je cours plus qu'il y a 3 mois",
        use_case="COMPARE_PERIODS",
        slots={
            "metric": "distance",
            "period_left": "last_3_months",
            "period_right": "previous_3_months",
        },
    ),
    # =====================================================
    # 🟦 COACHING — ANALYSE QUALITATIVE
    # =====================================================
    CatalogCase(
        text="est-ce que je progresse en ce moment",
        use_case="COACHING",
        slots={},
    ),
    CatalogCase(
        text="est-ce que mon entraînement est cohérent",
        use_case="COACHING",
        slots={},
    ),
    CatalogCase(
        text="donne-moi ton avis sur mon entraînement",
        use_case="COACHING",
        slots={},
    ),
    CatalogCase(
        text="est-ce que je m'entraîne trop",
        use_case="COACHING",
        slots={},
    ),
    CatalogCase(
        text="est-ce que je suis régulier dans mes entraînements",
        use_case="COACHING",
        slots={},
    ),
    CatalogCase(
        text="analyse ma charge d'entraînement récente",
        use_case="COACHING",
        slots={},
    ),
    # =====================================================
    # 🟦 RECOMMENDATION — QUE FAIRE ENSUITE
    # =====================================================
    CatalogCase(
        text="que me conseilles-tu pour la suite",
        use_case="RECOMMENDATION",
        slots={},
    ),
    CatalogCase(
        text="quelle séance devrais-je faire ensuite",
        use_case="RECOMMENDATION",
        slots={},
    ),
    CatalogCase(
        text="comment continuer à progresser",
        use_case="RECOMMENDATION",
        slots={},
    ),
]
