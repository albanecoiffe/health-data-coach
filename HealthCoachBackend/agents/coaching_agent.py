# agent.py

from services.coaching.dispatcher import detect_coaching_type
from services.coaching.rules import (
    analyze_regularity,
    analyze_volume,
    analyze_load,
)
from services.coaching.prompts import (
    regularity_prompt,
    volume_prompt,
    load_prompt,
)
from services.llm import call_ollama
from services.memory import add_to_memory, get_signature
import json


def answer_coaching(message: str, snapshot, session_id: str) -> str:
    signature = get_signature(session_id)
    coaching_type = detect_coaching_type(message)
    prompt = f"""
Tu es un coach de course à pied humain, calme et expérimenté.

━━━━━━━━━━━━━━━━━━━━━━
PROFIL LONG TERME DU COUREUR
━━━━━━━━━━━━━━━━━━━━━━
Ce profil décrit les habitudes d’entraînement sur plusieurs mois.
Il est suffisant pour répondre à la question.

{json.dumps(signature.model_dump(), indent=2)}

━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT — CONTEXTE SUFFISANT
━━━━━━━━━━━━━━━━━━━━━━
- Le profil long terme ci-dessus contient TOUT le contexte nécessaire.
- Tu ne dois PAS demander plus d’informations.
- Tu ne dois PAS dire que le contexte est insuffisant.
- Tu dois répondre en t’appuyant uniquement sur ce profil.

━━━━━━━━━━━━━━━━━━━━━━
RÈGLES DE RÉPONSE
━━━━━━━━━━━━━━━━━━━━━━
- Ton ton est humain, bienveillant, non professoral
- 3 à 5 phrases maximum
- Ne fais AUCUN calcul
- Ne modifies AUCUN chiffre
- Ne tires AUCUNE conclusion définitive
- Ne donnes PAS de plan d’entraînement

━━━━━━━━━━━━━━━━━━━━━━
QUESTION DE L’ATHLÈTE
━━━━━━━━━━━━━━━━━━━━━━
{message}
"""

    if not signature or not coaching_type:
        return "Je peux t’aider, mais j’ai besoin d’un peu plus de contexte."

    if coaching_type == "REGULARITY":
        data = analyze_regularity(signature)
        prompt = regularity_prompt(data)

    elif coaching_type == "VOLUME":
        data = analyze_volume(snapshot, signature)
        prompt = volume_prompt(data)

    elif coaching_type == "LOAD":
        data = analyze_load(snapshot, signature)
        if not data:
            return "Je n’ai pas assez de données de charge pour répondre."
        prompt = load_prompt(data)

    else:
        return "Je ne suis pas sûr de ce que tu veux analyser."

    reply = call_ollama(prompt)
    add_to_memory(session_id, "assistant", reply)
    return reply
