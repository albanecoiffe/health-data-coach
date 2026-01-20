# ============================================================
# Recommendation agent — verbalisation
# ============================================================

from typing import Dict, List
from recommendation.schemas import WeekRecommendation
from services.llm import call_ollama
from services.memory import add_to_memory, get_signature, get_memory


# ------------------------------------------------------------
# LLM
# ------------------------------------------------------------


def recommendation_to_text(reco: WeekRecommendation, session_id: str) -> str:
    signature = get_signature(session_id)
    memory = get_memory(session_id)
    already_started = any(m["role"] == "user" for m in memory)

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
    done_sessions_block = (
        "Aucune séance n’a encore été réalisée cette semaine."
        if not reco["done_sessions_details"]
        else reco["done_sessions_details"]
    )

    prompt = f"""
Tu es un coach de course à pied expérimenté.

Voici une recommandation structurée basée sur les données réelles
des dernières semaines d'entraînement de l'athlète.

RÈGLE ABSOLUE :
- Si {already_started} est vrai, ta réponse DOIT commencer directement
  par le contenu, sans aucune formule d’ouverture (pas de bonjour, salut, etc...).

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

{done_sessions_block}
- Si aucune séance n’a encore été réalisée, tu dois le dire explicitement
  et NE PAS analyser de séances passées.

INTERPRÉTATION :
- high_intensity_pct élevé → séance exigeante
- low_intensity_pct élevé → séance facile / récup
- Utilise ces données pour expliquer leur rôle
- Si toutes les séances prévues ont été réalisées, dis-le explicitement
- Quand la semaine est complète, toute référence aux séances passées
  doit explicitement mentionner "la semaine qui vient de s’achever"
  ou "les dernières semaines".

=================================
SÉANCES À PROGRAMMER
=================================

{reco["remaining_sessions"]}

- Les séances listées dans "SÉANCES À PROGRAMMER" n’ont PAS encore été réalisées.
- Tu ne dois jamais les décrire comme des séances déjà effectuées.


INTERPRÉTATION DES DONNÉES :
- low_intensity_pct > 0.85 → séance majoritairement facile
- high_intensity_pct > 0.45 → séance exigeante
- Une séance facile vise la récupération
- Une séance d’endurance vise la continuité, sans essoufflement

- Si aucune séance n’est proposée :
  - explique que toutes les séances prévues ont été réalisées
  - enchaîne naturellement vers la semaine suivante si le contexte l’indique

RÈGLE DE COHÉRENCE :
- Si risk_level est "high", le discours doit insister sur la récupération,
  la consolidation ou la stabilisation.
- Ne jamais associer "risque élevé" avec "accélérer", "maintenir le rythme"
  ou "augmenter la charge".

=================================
INSTRUCTIONS STRICTES
=================================
- Explique chaque séance en t'appuyant sur les données fournies
- Adapte le discours au contexte temporel (semaine en cours ou suivante)
- Ne modifie PAS le nombre de séances
- N’ajoute AUCUNE séance
- Ne contredis PAS le niveau de risque
- Si aucune séance n’est proposée, explique pourquoi

- Pour CHAQUE séance à programmer :
  - mentionne explicitement :
    • la durée moyenne (en minutes)
    • la distance moyenne (en km)
    • la répartition d’intensité (faible vs élevée)
- Les valeurs doivent provenir directement des données fournies
- N’utilise PAS de termes vagues sans les relier aux chiffres

- Lorsque des bornes min / max sont fournies pour une séance :
  - présente la valeur moyenne comme la cible principale
  - précise que cette cible peut varier dans une plage habituelle
  - utilise une formulation du type :
    "vise environ A, avec une variation possible entre X et Y"
    ou
    "une distance moyenne de A km, pouvant varier entre X et Y km"


Rédige une réponse claire, humaine et motivante.
"""

    reply = call_ollama(prompt)
    add_to_memory(session_id, "assistant", reply)

    return reply
