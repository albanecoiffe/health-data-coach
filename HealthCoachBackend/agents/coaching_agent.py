from services.coaching.dispatcher import detect_coaching_type
from services.coaching.rules import (
    analyze_regularity,
    analyze_volume,
    analyze_load,
)
from services.memory import get_memory
from services.llm import call_ollama
from services.memory import add_to_memory, get_signature
import json


def answer_coaching(message: str, snapshot, session_id: str) -> str:
    signature = get_signature(session_id)
    memory = get_memory(session_id)
    already_started = bool(memory)

    print("\n🧠 ANSWER_COACHING")
    print("📝 Message :", message)
    print("🧾 Session :", session_id)
    print("🧠 Signature présente :", signature is not None)
    print("🧠 Mémoire existante :", already_started)

    if not signature:
        return "Je peux t’aider, mais je n’ai pas encore assez d’historique."

    signature_dict = (
        signature.model_dump() if hasattr(signature, "model_dump") else signature
    )

    coaching_type = detect_coaching_type(message)
    print("🎯 Coaching type détecté :", coaching_type)

    if not coaching_type:
        return "Je peux t’aider, mais je ne suis pas sûr de ce que tu veux analyser."

    # ======================================================
    # 🧠 PROMPT GÉNÉRAL
    # ======================================================
    base_prompt = f"""
Tu es un coach de course à pied humain, calme et expérimenté.
Tu t’adresses à un coureur adulte, sans jargon inutile.
Réponds STRICTEMENT dans la langue du message utilisateur.

RÈGLE ABSOLUE :
- Si la conversation a déjà commencé ({already_started}),
  tu NE DOIS PAS dire bonjour, salut ou hello.

━━━━━━━━━━━━━━━━━━━━━━
PROFIL LONG TERME DU COUREUR
━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(signature_dict, indent=2)}
"""

    # ======================================================
    # 🧠 ANALYSE BACKEND + PROMPT SPÉCIALISÉ
    # ======================================================
    if coaching_type == "REGULARITY":
        facts = analyze_regularity(signature_dict)
        print("📊 Facts REGULARITY :", facts)
        specific_prompt = build_regularity_prompt(message, facts, already_started)

    elif coaching_type == "VOLUME":
        facts = analyze_volume(snapshot, signature_dict)
        print("📊 Facts VOLUME :", facts)
        specific_prompt = build_volume_prompt(message, facts, already_started)

    elif coaching_type == "LOAD":
        facts = analyze_load(snapshot, signature_dict)
        print("📊 Facts LOAD :", facts)

        if not facts:
            return "Je n’ai pas assez de données de charge pour répondre."

        specific_prompt = build_load_prompt(message, facts, already_started)

    else:
        return "Je ne suis pas sûr de ce que tu veux analyser."

    final_prompt = base_prompt + "\n\n" + specific_prompt

    print("🧾 PROMPT FINAL ENVOYÉ AU LLM")
    reply = call_ollama(final_prompt)

    add_to_memory(session_id, "assistant", reply)
    print("🗣️ Réponse LLM :", reply)

    return reply


def build_load_prompt(message, facts, already_started):
    return f"""
Tu es un coach de course à pied humain, calme et expérimenté.
Réponds dans la langue du message utilisateur.

RÈGLE ABSOLUE :
- Si la conversation a déjà commencé ({already_started}),
  tu NE DOIS PAS dire bonjour ou saluer.

━━━━━━━━━━━━━━━━━━━━━━
FAITS DE CHARGE (CALCULÉS PAR LE SYSTÈME)
━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(facts, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━
LEXIQUE — CHARGE (OBLIGATOIRE)
━━━━━━━━━━━━━━━━━━━━━━
- weekly_avg_load : charge moyenne hebdomadaire (≠ distance)
- weekly_std_load : variabilité de la charge
- acwr_avg : charge récente / charge habituelle
- acwr_max : pic ponctuel observé

INTERPRÉTATION AUTORISÉE :
- acwr proche de 1 → charge cohérente avec l’habitude
- acwr_max élevé → pics possibles mais ponctuels
- variabilité élevée → charge moins régulière

INTERDIT :
- Ne jamais parler de kilomètres
- Ne jamais inventer une tendance
- Ne jamais médicaliser ou diagnostiquer

RÈGLE CRITIQUE :
- weekly_avg_load, weekly_std_load, acwr_* ne sont PAS des distances
- Tu dois les appeler explicitement "charge" ou "indice de charge"
- Tu ne dois JAMAIS utiliser l’unité "km" ou "kilomètres"

EXEMPLE CORRECT :
"une charge moyenne hebdomadaire de 258 unités de charge"
EXEMPLE INTERDIT :
"258 km", "258 kilomètres", "volume de 258 km"
━━━━━━━━━━━━━━━━━━━━━━
RÈGLES DE RÉPONSE
━━━━━━━━━━━━━━━━━━━━━━
- Mentionne au moins 2 métriques chiffrées
- Pas de calcul, pas de plan, pas de diagnostic

QUESTION :
{message}
"""


def build_regularity_prompt(message, facts, already_started):
    return f"""
Tu es un coach de course à pied humain, bienveillant et précis.
Réponds dans la langue du message utilisateur.

RÈGLE ABSOLUE :
- Si la conversation a déjà commencé ({already_started}),
  tu NE DOIS PAS saluer.

━━━━━━━━━━━━━━━━━━━━━━
FAITS DE RÉGULARITÉ
━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(facts, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━
LEXIQUE — RÉGULARITÉ
━━━━━━━━━━━━━━━━━━━━━━
- weeks_with_runs_pct : proportion de semaines avec au moins une séance
- longest_break_days : plus longue coupure observée
- weekly_std_sessions : stabilité du nombre de séances

INTERPRÉTATION AUTORISÉE :
- régularité = constance dans le temps
- stabilité = peu de variations hebdomadaires

━━━━━━━━━━━━━━━━━━━━━━
RÈGLES DE RÉPONSE
━━━━━━━━━━━━━━━━━━━━━━
- Mentionne au moins 2 métriques
- Pas de jugement définitif
- Pas de plan d’entraînement

QUESTION :
{message}
"""


def build_volume_prompt(message, facts, already_started):
    return f"""
Tu es un coach de course à pied humain, clair et pédagogique.
Réponds dans la langue du message utilisateur.

RÈGLE ABSOLUE :
- Si la conversation a déjà commencé ({already_started}),
  tu NE DOIS PAS saluer.

━━━━━━━━━━━━━━━━━━━━━━
FAITS DE VOLUME
━━━━━━━━━━━━━━━━━━━━━━
{json.dumps(facts, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━
LEXIQUE — VOLUME
━━━━━━━━━━━━━━━━━━━━━━
- weekly_km : volume de la semaine courante
- habit_km : volume hebdomadaire habituel
- status : position par rapport à l’habitude

INTERPRÉTATION AUTORISÉE :
- comparaison semaine vs habitude
- commentaire de cohérence globale

━━━━━━━━━━━━━━━━━━━━━━
RÈGLES DE RÉPONSE
━━━━━━━━━━━━━━━━━━━━━━
- Mentionne au moins 2 métriques
- Pas de seuils médicaux
- Pas de plan d’entraînement

QUESTION :
{message}
"""
