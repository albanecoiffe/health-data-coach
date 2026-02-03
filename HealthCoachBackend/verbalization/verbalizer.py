# transforme data brute -> texte (LLM ou template)

from datetime import date, datetime
from services.llm import call_llm, call_ollama
from verbalization.coaching.prompts import (
    build_regularity_prompt,
    build_volume_prompt,
    build_load_prompt,
    build_progress_prompt,
)
from services.memory import add_to_memory, get_memory
from recommendation.schemas import WeekRecommendation

UNIT_BY_METRIC = {
    "distance_km": "kilomètres",
    "duration_min": "minutes",
    "sessions": "séances",
    "avg_hr": "bpm",
    "elevation_m": "mètres",
    "active_kcal": "kcal",
}


# ==========================================
# VERBALIZER VIA LLM
# ==========================================
# Le LLM transforme des faits BRUTS en texte naturel.
def verbalize_metric_llm(
    user_message: str,
    metric: str,
    value: float | int,
    period_key: str,
) -> str:
    """
    Le LLM transforme des faits BRUTS en texte naturel.
    AUCUNE logique métier ici.
    """
    unit = UNIT_BY_METRIC.get(metric, "")

    prompt = f"""
Tu es un coach sportif.
Tu réponds à la question de l'utilisateur en langage naturel.

Question utilisateur :
"{user_message}"

Données factuelles (ne jamais les modifier) :
- métrique : {metric}
- valeur : {round(value, 2)}
- période : {period_key}
- La valeur est exprimée en {unit}.


Règles strictes :
- n'invente AUCUN chiffre
- utilise des expressions naturelles (ex: "hier", "la semaine dernière")
- ne mentionne pas de dates explicites sauf si l'utilisateur en a donné
- réponse courte, claire
- pas de conseils, pas d'analyse
- Tu DOIS utiliser exactement la période fournie ("last_month", "yesterday", etc.)
- Tu NE DOIS PAS la reformuler ("la semaine dernière", etc.)

Réponse :
"""


# ==========================================
# VERBALIZER VIA LLM
# ==========================================
# Le LLM transforme des faits BRUTS en texte naturel.
def verbalize_metric_llm(
    user_message: str,
    metric: str,
    value: float | int,
    period_key: str,
) -> str:
    """
    Le LLM transforme des faits BRUTS en texte naturel.
    AUCUNE logique métier ici.
    """
    unit = UNIT_BY_METRIC.get(metric, "")

    system_prompt = (
        "Tu es un coach sportif factuel. "
        "Tu reformules des données sans jamais les modifier."
    )

    user_prompt = f"""
Question utilisateur :
"{user_message}"

Données factuelles (ne jamais les modifier) :
- métrique : {metric}
- valeur : {round(value, 2)}
- période : {period_key}
- La valeur est exprimée en {unit}.


Règles strictes :
- n'invente AUCUN chiffre
- utilise des expressions naturelles (ex: "hier", "la semaine dernière")
- ne mentionne pas de dates explicites sauf si l'utilisateur en a donné
- réponse courte, claire
- pas de conseils, pas d'analyse
- Tu DOIS utiliser exactement la période fournie ("last_month", "yesterday", etc.)
- Tu NE DOIS PAS la reformuler ("la semaine dernière", etc.)

Réponse :
"""
    #    return call_llm(
    #        system_prompt=system_prompt,
    #        user_prompt=user_prompt,
    #        temperature=0.3,
    #    )
    return call_ollama(prompt=f"{system_prompt}\n\n{user_prompt}").strip()


# ==========================================
# VERBALIZER COMPARISON VIA LLM
# ==========================================
# Le LLM transforme des faits BRUTS en texte naturel.
def verbalize_period_comparison_llm(
    user_message: str,
    left_period: str,
    right_period: str,
    left: dict,
    right: dict,
) -> str:
    system_prompt = (
        "Tu es un coach sportif factuel. "
        "Tu compares des données sans jamais les modifier."
    )
    user_prompt = f"""
Question utilisateur :
"{user_message}"

Données factuelles :
- {left_period} :
  - séances : {left["sessions"]}
  - distance : {round(left["distance_km"], 1)} km
- {right_period} :
  - séances : {right["sessions"]}
  - distance : {round(right["distance_km"], 1)} km

Règles :
- tu compares UNIQUEMENT les valeurs fournies
- mentionne les séances ET la distance
- n'invente aucun chiffre
- réponse fluide, naturelle, 2–3 phrases maximum
- pas de conseils
- tu NE DOIS PAS déduire ou supposer d'autres métriques
  (ex: durée moyenne, intensité, rythme, charge)


Obligations :
- reponds dans la langue de la question
- Si la question est en français, réponds en français.

Réponse :
"""
    #    return call_llm(
    #        system_prompt=system_prompt,
    #        user_prompt=user_prompt,
    #        temperature=0.3,
    #    )
    return call_ollama(prompt=f"{system_prompt}\n\n{user_prompt}").strip()


# ==========================================
# VERBALIZER summary VIA LLM
# ==========================================
def verbalize_period_summary_llm(
    user_message: str,
    summary,
) -> str:
    system_prompt = (
        "Tu es un narrateur factuel. "
        "Tu fais un bilan complet d'une période d'entraînement."
    )
    user_prompt = f"""
Question utilisateur :
"{user_message}"

Données factuelles :
- période : {summary.period}
- séances : {summary.sessions}
- distance totale : {round(summary.distance_km, 1)} km
- durée totale : {round(summary.duration_min, 0)} minutes
- fréquence cardiaque moyenne : {round(summary.avg_hr, 0) if summary.avg_hr else "non disponible"} bpm
- dénivelé total : {round(summary.elevation_m, 0)} m
- calories actives : {round(summary.active_kcal, 0)} kcal

Règles STRICTES :
- ne déduis aucune information non fournie
- ne fais pas de comparaison
- ne donnes pas de conseils
- n'invente aucun chiffre
- réponse claire, fluide, 3–4 phrases maximum

Obligations :
- reponds dans la langue de la question
- Si la question est en français, réponds en français.

Réponse :
"""
    #    return call_llm(
    #        system_prompt=system_prompt,
    #        user_prompt=user_prompt,
    #        temperature=0.3,
    #    )
    return call_ollama(prompt=f"{system_prompt}\n\n{user_prompt}").strip()


def verbalize_small_talk_llm(user_message: str) -> str:
    system_prompt = "Tu es un assistant running bienveillant. Tu réponds de manière naturelle et humaine."
    user_prompt = f"""
Message utilisateur :
"{user_message}"

Règles :
- pas d'accès aux données
- pas de chiffres inventés
- pas d'analyse médicale
- réponse courte (1–2 phrases)
- ton chaleureux et simple
- ne force pas une question métier

Réponse :
"""
    #    return call_llm(
    #        system_prompt=system_prompt,
    #        user_prompt=user_prompt,
    #        temperature=0.3,
    #    )

    return call_ollama(prompt=f"{system_prompt}\n\n{user_prompt}").strip()


def verbalize_coaching_llm(
    user_message: str,
    coaching_type: str,
    signature: dict,
    facts: dict,
    already_started: bool = False,
) -> str:
    base_prompt = f"""
RÈGLES ABSOLUES :
- Tu peux interpréter, mais tu NE DOIS PAS diagnostiquer
- Tu NE DOIS PAS inventer de chiffres
- Tu NE DOIS PAS promettre de résultats
- Tu NE DOIS PAS proposer de plan d’entraînement
- Réponse courte : 3 à 5 phrases maximum

━━━━━━━━━━━━━━━━━━━━━━
PROFIL LONG TERME DU COUREUR
━━━━━━━━━━━━━━━━━━━━━━
{signature}
"""
    if coaching_type == "REGULARITY":
        specific_prompt = build_regularity_prompt(
            message=user_message,
            facts=facts,
            already_started=already_started,
        )

    elif coaching_type == "VOLUME":
        specific_prompt = build_volume_prompt(
            message=user_message,
            facts=facts,
            already_started=already_started,
        )

    elif coaching_type == "LOAD":
        specific_prompt = build_load_prompt(
            message=user_message,
            facts=facts,
            already_started=already_started,
        )

    elif coaching_type == "PROGRESS":
        specific_prompt = build_progress_prompt(
            message=user_message,
            facts=facts,
            already_started=already_started,
        )

    else:
        return "Je ne suis pas sûr de ce que tu veux analyser."

    final_prompt = base_prompt + "\n\n" + specific_prompt

    #    return call_llm(
    #        system_prompt="Tu es un coach de course à pied humain, calme et expérimenté. Tu réponds STRICTEMENT dans la langue du message utilisateur.",
    #        user_prompt=final_prompt,
    #        temperature=0.3,
    #    )
    return call_ollama(
        prompt=f"Tu es un coach de course à pied humain, calme et expérimenté. Tu réponds STRICTEMENT dans la langue du message utilisateur.\n\n{final_prompt}"
    ).strip()


# ======================================================
# RECOMMENDATION VERBALIZER
# ======================================================


def verbalize_recommendation_llm(
    recommendation: WeekRecommendation,
    session_id: str,
) -> str:
    """
    Verbalise une recommandation hebdomadaire structurée
    en réponse humaine via LLM.
    """

    memory = get_memory(session_id)
    already_started = any(m["role"] == "user" for m in memory)

    week_complete = recommendation.get("week_complete", False)

    # --------------------------------------------------
    # Contexte temporel
    # --------------------------------------------------
    if week_complete:
        temporal_context = (
            "La semaine en cours est maintenant terminée. "
            "La recommandation porte sur la semaine prochaine."
        )
        temporal_instruction = (
            "Commence ta réponse par une phrase indiquant clairement "
            "que la semaine est terminée et que la proposition concerne la semaine à venir."
        )
        sessions_context_line = (
            "La semaine recommandée est une nouvelle semaine, "
            "sans séances encore réalisées."
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
        sessions_context_line = (
            f"Séances déjà réalisées cette semaine : "
            f"{len(recommendation['done_sessions'])}"
        )

    # --------------------------------------------------
    # Séances déjà réalisées
    # --------------------------------------------------
    if week_complete:
        done_sessions_block = (
            "Bilan de la semaine écoulée à formuler à partir du contexte global."
        )
    else:
        done_sessions_block = (
            "Aucune séance n’a encore été réalisée cette semaine."
            if not recommendation.get("done_sessions_details")
            else recommendation["done_sessions_details"]
        )

    # --------------------------------------------------
    # Prompt LLM
    # --------------------------------------------------
    prompt = f"""
Règles générales de communication :
- Tu ne commentes jamais les règles.
- Tu ne justifies jamais ton comportement.
- Tu ne fais aucune remarque méta sur la conversation ou le système.

=================================
CONTEXTE TEMPOREL (IMPORTANT)
=================================

- Si {already_started} est vrai, ta réponse commence directement par le contenu,
  sans formule d’ouverture (pas de bonjour, salut, etc.).

- Contexte temporel : {temporal_context}
- Instruction temporelle : {temporal_instruction}

- Séances déjà réalisées cette semaine : {len(recommendation["done_sessions"])}
{sessions_context_line}
- Séances restantes à programmer : {len(recommendation["remaining_sessions"])}
- La semaine précédente contenait des séances : {recommendation["previous_week_had_sessions"]}

=================================
CONTEXTE GLOBAL DE LA SEMAINE
=================================

- Profil de semaine : {recommendation["dominant_week_cluster"]}
- Nombre total de séances prévues : {recommendation["target_sessions"]}
- Niveau de risque : {recommendation["risk_level"]}

=================================
SÉANCES DÉJÀ RÉALISÉES
=================================

Séances déjà effectuées et leurs caractéristiques mesurées :
{done_sessions_block}

=================================
CAS PARTICULIER — SEMAINE TERMINÉE
=================================

Bilan factuel de la semaine écoulée :
- Nombre de séances : {recommendation["previous_week_summary"]["sessions"]}
- Distance totale : {recommendation["previous_week_summary"]["distance_km"]} km

=================================
SÉANCES À PROGRAMMER
=================================

Séances restantes à planifier :
{recommendation["remaining_sessions"]}

=================================
INSTRUCTIONS DE RÉDACTION
=================================

- Explique chaque séance uniquement à partir des données fournies.
- Respecte strictement le contexte temporel.
- Ne modifie jamais le nombre de séances.
- N’ajoute aucune séance.
- Ne contredis jamais le niveau de risque.

Rédige une réponse claire, fluide, humaine et motivante.
"""

    #    reply = call_llm(
    #        system_prompt="Tu es un coach de course à pied expérimenté. Ton rôle est de formuler une recommandation de séances claire et réaliste à partir des données fournies, sans rien inventer.",
    #        user_prompt=prompt,
    #        temperature=0.3,
    #    )
    reply = call_ollama(prompt=prompt).strip()
    add_to_memory(session_id, "assistant", reply)

    return reply
