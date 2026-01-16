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

    prompt = f"""
Tu es un coach de course à pied expérimenté.

Voici une recommandation structurée basée sur les données réelles
des dernières semaines d'entraînement de l'athlète.

RÈGLE ABSOLUE :
- Si la conversation a déjà commencé ({already_started}),
  tu NE DOIS PAS dire bonjour, salut ou hello.

=================================
CONTEXTE GLOBAL DE LA SEMAINE
=================================

- Profil de semaine : {reco["dominant_week_cluster"]}
- Nombre de séances recommandées : {reco["target_sessions"]}
- Niveau de risque : {reco["risk_level"]}

=================================
SÉANCES DÉJÀ RÉALISÉES CETTE SEMAINE
=================================

Voici les séances déjà effectuées, avec leurs caractéristiques mesurées :

{reco["done_sessions_details"]}

INTERPRÉTATION :
- high_intensity_pct élevé → séance exigeante
- low_intensity_pct élevé → séance facile / récup
- Utilise ces données pour expliquer le rôle de ces séances
  dans l’équilibre global de la semaine

RÈGLE :
- Ne laisse AUCUN champ vide
- Ne crée PAS de placeholders
- Si une seule séance a été faite, explique son impact sur la suite


=================================
SÉANCES RESTANTES À EFFECTUER
=================================


Voici les séances recommandées pour le reste de la semaine,
avec leurs profils moyens basés sur les données de l’athlète :

{reco["remaining_sessions"]}

INTERPRÉTATION DES DONNÉES (IMPORTANT) :
- low_intensity_pct > 0.85 signifie une séance majoritairement facile
- high_intensity_pct > 0.45 signifie une séance exigeante / intense
- Une séance facile vise la récupération, pas le progrès immédiat
- Une séance d’endurance vise la continuité de l’effort, sans essoufflement


=================================
INSTRUCTIONS STRICTES
=================================
- Explique chaque séance en t'appuyant sur les données fournies
- Interprète les pourcentages d'intensité et durées
- Adapte le ton à un coach bienveillant
- Ajoute des conseils pratiques (respiration, ressenti, récupération)
- Ne modifie PAS le nombre de séances
- N’ajoute AUCUNE séance
- Ne contredis PAS le niveau de risque

Rédige une réponse claire et motivante.
"""

    return call_ollama(prompt)
