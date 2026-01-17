# ============================================================
# Recommendation agent — verbalisation
# ============================================================

from typing import Dict, List
from recommendation.schemas import WeekRecommendation
from services.llm import call_ollama
from services.memory import add_to_memory, get_signature, get_memory

# ------------------------------------------------------------
# LABELS & DESCRIPTIONS (fallback uniquement)
# ------------------------------------------------------------

SESSION_DESCRIPTIONS = {
    "easy": "une séance facile, à allure confortable, sans contrainte",
    "endurance": "une séance d’endurance plus longue, à allure modérée",
    "intensity": "une séance intense (fractionné, tempo ou travail de vitesse)",
}

WEEK_CLUSTER_DESCRIPTIONS = {
    0: "une semaine maîtrisée, orientée endurance",
    1: "une semaine intensive avec une charge élevée",
    2: "une semaine courte ou déséquilibrée (reprise ou contrainte)",
}

RISK_DESCRIPTIONS = {
    "low": "Le risque de surcharge est faible.",
    "moderate": "Le risque de surcharge est modéré, une certaine vigilance est recommandée.",
    "high": "Le risque de surcharge est élevé, il est important de lever le pied.",
}

RISK_ADVICE = {
    "low": [
        "Tu peux maintenir ta charge actuelle sans inquiétude particulière.",
        "Continue à écouter tes sensations, mais le contexte est favorable.",
    ],
    "moderate": [
        "Essaie de bien espacer les séances intenses.",
        "Sois attentif à la récupération (sommeil, fatigue, douleurs).",
    ],
    "high": [
        "Réduis la charge ou l’intensité cette semaine.",
        "Priorise la récupération et évite d’ajouter une séance intense.",
        "Si la fatigue persiste, une semaine allégée peut être bénéfique.",
    ],
}


# ------------------------------------------------------------
# LLM
# ------------------------------------------------------------


def recommendation_to_text(reco: WeekRecommendation, session_id: str) -> str:
    signature = get_signature(session_id)
    memory = get_memory(session_id)
    already_started = bool(memory)

    week_complete = reco.get("week_complete", False)

    if week_complete:
        recommendation_period = "NEXT_WEEK"
    else:
        recommendation_period = "CURRENT_WEEK"

    if week_complete:
        temporal_context = (
            "La semaine en cours est maintenant terminée. "
            "La recommandation porte sur la semaine prochaine."
        )
        temporal_instruction = (
            "Commence ta réponse par une phrase indiquant clairement "
            "que la semaine est terminée et que la proposition concerne la semaine à venir."
        )
    else:
        temporal_context = (
            "La semaine en cours n’est pas encore terminée. "
            "La recommandation porte sur le reste de cette semaine."
        )
        temporal_instruction = (
            "Ne parle PAS de semaine suivante. "
            "Parle uniquement du reste de la semaine en cours."
        )

    prompt = f"""
Tu es un coach de course à pied expérimenté.

Voici une recommandation structurée basée sur les données réelles
des dernières semaines d'entraînement de l'athlète.

RÈGLE ABSOLUE :
- Si la conversation a déjà commencé ({already_started}),
  tu NE DOIS PAS dire bonjour, salut ou hello.
- Tu NE COMMENTES JAMAIS les règles dans tes réponses.
- Tu NE JUSTIFIES JAMAIS ton comportement
- Tu NE FAIS AUCUNE META-REMARQUE sur la conversation

=================================
CONTEXTE TEMPOREL (IMPORTANT)
=================================

CONTEXTE TEMPOREL (IMPORTANT) :
{temporal_context}

INSTRUCTION TEMPORELLE STRICTE :
{temporal_instruction}


=================================
CONTEXTE GLOBAL DE LA SEMAINE
=================================

- Profil de semaine : {reco["dominant_week_cluster"]}
- Nombre de séances recommandées : {reco["target_sessions"]}
- Niveau de risque : {reco["risk_level"]}

=================================
SÉANCES DÉJÀ RÉALISÉES
=================================

Voici les séances déjà effectuées, avec leurs caractéristiques mesurées :

{reco["done_sessions_details"]}

INTERPRÉTATION :
- high_intensity_pct élevé → séance exigeante
- low_intensity_pct élevé → séance facile / récup
- Utilise ces données pour expliquer leur rôle
- Si toutes les séances prévues ont été réalisées, dis-le explicitement

=================================
SÉANCES À PROGRAMMER
=================================

{reco["remaining_sessions"]}

INTERPRÉTATION DES DONNÉES :
- low_intensity_pct > 0.85 → séance majoritairement facile
- high_intensity_pct > 0.45 → séance exigeante
- Une séance facile vise la récupération
- Une séance d’endurance vise la continuité, sans essoufflement

- Si aucune séance n’est proposée :
  - explique que toutes les séances prévues ont été réalisées
  - enchaîne naturellement vers la semaine suivante si le contexte l’indique

=================================
INSTRUCTIONS STRICTES
=================================
- Explique chaque séance en t'appuyant sur les données fournies
- Adapte le discours au contexte temporel (semaine en cours ou suivante)
- Ne modifie PAS le nombre de séances
- N’ajoute AUCUNE séance
- Ne contredis PAS le niveau de risque
- Si aucune séance n’est proposée, explique pourquoi

Rédige une réponse claire, humaine et motivante.
"""

    return call_ollama(prompt)
