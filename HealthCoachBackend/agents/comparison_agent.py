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
- Tu ne donnes AUCUN chiffre
- Tu ne cites AUCUNE métrique (distance, durée, séances, etc.)
- Tu ne fais AUCUNE interprétation
- Tu ne donnes AUCUN conseil
- Tu parles UNIQUEMENT des deux périodes fournies
- Tu présentes TOUJOURS la période récente en premier
- Tu ne mentionnes JAMAIS UP, DOWN ou STABLE
- Tu n’utilises AUCUN mot vague ou creux

━━━━━━━━━━━━━━━━━━━━━━
STRUCTURE OBLIGATOIRE
━━━━━━━━━━━━━━━━━━━━━━
- Tu écris UNE SEULE phrase.
- Tu indiques EXPLICITEMENT quelle période est la plus active,
  ou si elles sont équivalentes.

- Tu dois produire UNE assertion logique unique.
    - Si la période A est plus active → tu dis qu’elle est plus active.
    - Si la période B est plus active → tu dis qu’elle est plus active.
    - Si les périodes sont équivalentes → tu dis qu’elles sont similaires.

QUESTION UTILISATEUR :
"{message}"
"""

    return call_ollama(prompt)


def get_distance(run):
    return getattr(run, "distance_km", None) or getattr(run, "distanceKm", None) or 0
