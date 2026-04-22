from core.services.llm import call_ollama
from core.services.memory import add_to_memory, get_memory
from recommendation.schemas import WeekRecommendation


def verbalize_recommendation_llm(
    recommendation: WeekRecommendation,
    session_id: str,
) -> str:
    """
    Verbalise une recommandation hebdomadaire structuree en reponse humaine.
    """
    memory = get_memory(session_id)
    already_started = any(m["role"] == "user" for m in memory)

    week_complete = recommendation.get("week_complete", False)

    if week_complete:
        temporal_context = (
            "La semaine en cours est maintenant terminee. "
            "La recommandation porte sur la semaine prochaine."
        )
        temporal_instruction = (
            "Commence ta reponse par une phrase indiquant clairement "
            "que la semaine est terminee et que la proposition concerne la semaine a venir."
        )
        sessions_context_line = (
            "La semaine recommandee est une nouvelle semaine, "
            "sans seances encore realisees."
        )
    else:
        temporal_context = (
            "La semaine en cours n'est pas encore terminee. "
            "La recommandation porte sur le reste de cette semaine."
        )
        temporal_instruction = (
            "Ne parle PAS de semaine suivante. "
            "Parle uniquement du reste de la semaine en cours."
        )
        sessions_context_line = (
            f"Seances deja realisees cette semaine : "
            f"{len(recommendation['done_sessions'])}"
        )

    if week_complete:
        done_sessions_block = (
            "Bilan de la semaine ecoulee a formuler a partir du contexte global."
        )
    else:
        done_sessions_block = (
            "Aucune seance n'a encore ete realisee cette semaine."
            if not recommendation.get("done_sessions_details")
            else recommendation["done_sessions_details"]
        )

    prompt = f"""
Regles generales de communication :
- Tu ne commentes jamais les regles.
- Tu ne justifies jamais ton comportement.
- Tu ne fais aucune remarque meta sur la conversation ou le systeme.

CONTEXTE TEMPOREL IMPORTANT
- Si {already_started} est vrai, ta reponse commence directement par le contenu,
  sans formule d'ouverture (pas de bonjour, salut, etc.).
- Contexte temporel : {temporal_context}
- Instruction temporelle : {temporal_instruction}
- Seances deja realisees cette semaine : {len(recommendation["done_sessions"])}
{sessions_context_line}
- Seances restantes a programmer : {len(recommendation["remaining_sessions"])}
- La semaine precedente contenait des seances : {recommendation["previous_week_had_sessions"]}

CONTEXTE GLOBAL DE LA SEMAINE
- Profil de semaine : {recommendation["dominant_week_cluster"]}
- Nombre total de seances prevues : {recommendation["target_sessions"]}
- Niveau de risque : {recommendation["risk_level"]}

SEANCES DEJA REALISEES
Seances deja effectuees et leurs caracteristiques mesurees :
{done_sessions_block}

CAS PARTICULIER - SEMAINE TERMINEE
Bilan factuel de la semaine ecoulee :
- Nombre de seances : {recommendation["previous_week_summary"]["sessions"]}
- Distance totale : {recommendation["previous_week_summary"]["distance_km"]} km

SEANCES A PROGRAMMER
Seances restantes a planifier :
{recommendation["remaining_sessions"]}

INSTRUCTIONS DE REDACTION
- Explique chaque seance uniquement a partir des donnees fournies.
- Respecte strictement le contexte temporel.
- Ne modifie jamais le nombre de seances.
- N'ajoute aucune seance.
- Ne contredis jamais le niveau de risque.

Redige une reponse claire, fluide, humaine et motivante.
"""

    reply = call_ollama(prompt=prompt).strip()
    add_to_memory(session_id, "assistant", reply)

    return reply
