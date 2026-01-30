import json
from services.llm import call_ollama
from intent_based_querying.normalization.normalizer import safe_json_load

SYSTEM_PROMPT = """
You are an intent extractor.

Return ONLY a valid JSON object.
No explanation. No text.

Allowed intents:
- GET_METRIC
- COMPARE_PERIODS
- PERIOD_SUMMARY
- COACHING
- SMALL_TALK

Allowed metrics:
- DISTANCE
- DURATION
- SESSIONS
- AVG_HR
- ELEVATION
- ACTIVE_KCAL

Allowed periods:
- today
- yesterday
- this_week
- last_week
- last_7_days
- this_month
- last_month
- this_year
- last_year
- relative days
- relative weeks
- relative months
- relative years

Example:
{
  "intent": "GET_METRIC",
  "metric": "DISTANCE",
  "period": "yesterday"
}

PRIORITÉ ABSOLUE :
Si le message parle de l’entraînement du coureur,
de sa régularité, de sa progression, de sa charge,
ou de la cohérence de sa pratique,
ALORS l’intent est COACHING,
MÊME si la question est courte ou non chiffrée.

Regles COACHING:
Utilise l’intent COACHING si l’utilisateur :
- parle de régularité, progression, charge, cohérence
- demande une analyse de sa pratique
- parle de lui ("je", "mon entraînement", "ma pratique")

Regles SMALL_TALK:
Utilise SMALL_TALK UNIQUEMENT si le message :
- est purement social (bonjour, merci, ça va ?)
- ne concerne PAS l’entraînement ou la pratique sportive

"""


def detect_intent(message: str) -> dict:
    prompt = f"{SYSTEM_PROMPT}\nUser message: {message}"
    raw = call_ollama(prompt)
    print("🟣 LLM RAW OUTPUT :", raw)
    intent = safe_json_load(raw)
    print("🟢 PARSED INTENT :", intent)

    intent["original_message"] = message
    print("\n🧠 INTENT DETECTION")
    print("➡️ Prompt sent to LLM")
    try:
        return intent

    except Exception:
        raise ValueError("Invalid intent JSON from LLM")
