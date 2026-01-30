# transforme data brute -> texte (LLM ou template)
# intent_based_querying/verbalizer.py

from datetime import date, datetime
from services.llm import call_ollama
from intent_based_querying.verbalization.coaching.prompts import (
    build_regularity_prompt,
    build_volume_prompt,
    build_load_prompt,
    build_progress_prompt,
)

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
    return call_ollama(prompt).strip()


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
    prompt = f"""
Tu es un coach sportif factuel.
Tu compares deux périodes d'entraînement.

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
    return call_ollama(prompt).strip()


# ==========================================
# VERBALIZER summary VIA LLM
# ==========================================
def verbalize_period_summary_llm(
    user_message: str,
    summary,
) -> str:
    prompt = f"""
Tu es un narrateur factuel.
Tu fais un bilan complet d'une période d'entraînement.

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
    return call_ollama(prompt).strip()


def verbalize_small_talk_llm(user_message: str) -> str:
    prompt = f"""
Tu es un assistant running bienveillant.
Tu réponds de manière naturelle et humaine.

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
    return call_ollama(prompt).strip()


def verbalize_coaching_llm(
    user_message: str,
    coaching_type: str,
    signature: dict,
    facts: dict,
    already_started: bool = False,
) -> str:
    base_prompt = f"""
Tu es un coach de course à pied humain, calme et expérimenté.
Tu réponds STRICTEMENT dans la langue du message utilisateur.

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
    return call_ollama(final_prompt)
