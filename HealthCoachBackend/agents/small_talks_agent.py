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


def answer_small_talk(message: str, session_id: str) -> str:
    memory = get_memory(session_id)
    already_started = any(m["role"] == "assistant" for m in memory)
    memory_text = ""
    if memory:
        memory_text = "\n".join(f"{m['role']}: {m['content']}" for m in memory)

    if already_started:
        prompt = f"""
Tu es un coach sportif humain spécialisé dans le running, sympa et bienveillant.

Contexte conversationnel :
{memory_text}

Règles strictes :
- La conversation est déjà entamée
- Tu NE SALUES PAS (pas de bonjour, salut, hello), SAUF si l'utilisateur te salue, alors tu le salue en retour
- Tu NE PARLES PAS d'entraînement, de chiffres ou de données sportives
- Tu peux répondre chaleureusement
- Tu peux poser une petite question sociale
- Réponse courte (1–2 phrases max)

Message utilisateur :
"{message}"
"""
    else:
        prompt = f"""
Tu es un coach sportif humain spécialisé dans le running, sympa et bienveillant.

Contexte :
- Début de la conversation
- Tu peux saluer UNE SEULE FOIS, sauf si l'utilisateur te salue, alors tu le salue en retour
- Tu NE PARLES PAS d'entraînement ni de données sportives
- Tu peux poser une petite question sociale
- Réponse courte (1–2 phrases max)

Message utilisateur :
"{message}"
"""

    reply = call_ollama(prompt)

    add_to_memory(session_id, "user", message)
    add_to_memory(session_id, "assistant", reply)

    return reply
