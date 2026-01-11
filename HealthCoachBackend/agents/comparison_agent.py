import json
from datetime import date, timedelta
from services.llm import call_ollama
import calendar
import json
from services.memory import (
    get_memory,
    add_to_memory,
    get_signature,
)


def comparison_response_agent(
    message: str,
    metric: str,
    delta: dict,
    left_period: tuple[str, str],
    right_period: tuple[str, str],
    period_context: str | None = None,
) -> str:
    """
    Génère UNIQUEMENT le texte humain.
    Aucun chiffre.
    Aucune interprétation.
    Deux phrases maximum.
    """

    prompt = f"""
Tu es un coach de course à pied humain, clair et naturel.

Tu compares deux périodes STRICTEMENT définies par leurs dates.

PÉRIODES :
- Du {left_period[0]} au {left_period[1]}
- Du {right_period[0]} au {right_period[1]}

TENDANCE GLOBALE FOURNIE PAR LE SYSTÈME :
- UP     → la seconde période est plus élevée
- DOWN   → la première période est plus élevée
- STABLE → volumes très proches

Tendance : {delta["trend"]}

━━━━━━━━━━━━━━━━━━━━━━
RÈGLES ABSOLUES
━━━━━━━━━━━━━━━━━━━━━━
- Tu écris EXACTEMENT DEUX PHRASES
- Tu ne donnes AUCUN chiffre
- Tu ne répètes PAS les métriques
- Tu ne fais AUCUNE interprétation
- Tu ne donnes AUCUN conseil
- Tu parles UNIQUEMENT avec les dates fournies
- Tu ne fais AUCUN méta-commentaire
- Tu présentes toujours la comparaison en partant de la période la plus récente
- Tu ne mentionnes jamais UP, DOWN ou STABLE dans le texte
- Tu ne mentionnes JAMAIS d’autre période que celles fournies
- Tu n’emploies AUCUNE référence temporelle externe (année, saison, cycle, historique, passé)
- Toute comparaison doit porter UNIQUEMENT sur les deux périodes données

━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE OBLIGATOIRE
━━━━━━━━━━━━━━━━━━━━━━
1) Phrase décrivant la période la plus récente
2) Phrase indiquant l’évolution par rapport à l’autre période

STYLE :
- Naturel
- Fluide
- Neutre

QUESTION UTILISATEUR :
"{message}"
"""

    return call_ollama(prompt)


def get_distance(run):
    return getattr(run, "distance_km", None) or getattr(run, "distanceKm", None) or 0
