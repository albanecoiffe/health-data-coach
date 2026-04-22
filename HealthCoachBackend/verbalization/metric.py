from core.services.llm import call_ollama
from verbalization.units import UNIT_BY_METRIC


def verbalize_metric_llm(
    user_message: str,
    metric: str,
    value: float | int,
    period_key: str,
) -> str:
    """
    Le LLM transforme des faits bruts en texte naturel.
    Aucune logique metier ici.
    """
    unit = UNIT_BY_METRIC.get(metric, "")

    system_prompt = (
        "Tu es un coach sportif factuel. "
        "Tu reformules des donnees sans jamais les modifier."
    )

    user_prompt = f"""
Question utilisateur :
"{user_message}"

Donnees factuelles (ne jamais les modifier) :
- metrique : {metric}
- valeur : {round(value, 2)}
- periode : {period_key}
- La valeur est exprimee en {unit}.


Regles strictes :
- n'invente AUCUN chiffre
- utilise des expressions naturelles (ex: "hier", "la semaine derniere")
- ne mentionne pas de dates explicites sauf si l'utilisateur en a donne
- reponse courte, claire
- pas de conseils, pas d'analyse
- Tu DOIS utiliser exactement la periode fournie ("last_month", "yesterday", etc.)
- Tu NE DOIS PAS la reformuler ("la semaine derniere", etc.)

Reponse :
"""
    return call_ollama(prompt=f"{system_prompt}\n\n{user_prompt}").strip()
