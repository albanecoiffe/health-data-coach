import json
from core.services.llm import call_ollama
from normalization.normalizer import safe_json_load

SYSTEM_PROMPT = """
You are an intent extractor.

Return ONLY a valid JSON object.
No explanation. No text.

Allowed intents:
- GET_METRIC
- COMPARE_PERIODS
- PERIOD_SUMMARY
- COACHING
- RECOMMENDATION
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
- last_X_days
- this_month
- last_month
- last_X_months
- this_year
- last_year
- last_X_years
- relative days
- relative weeks
- relative months
- relative years
- named_month

Example:
{
  "intent": "GET_METRIC",
  "metric": "DISTANCE",
  "period": "yesterday"
}

========================================
1 - SMALL_TALK
========================================
- Si le message est une salutation ou une phrase vague
    (ex: "hello", "salut", "bonjour", "ça va", "merci", "ok") :

Retourne EXACTEMENT :
- "intent": "SMALL_TALK",

- Tu n’as PAS le droit de demander des données supplémentaires dans ce cas.

- Si la phrase contient un indicateur quantitatif
    (distance, km, temps, durée, séance, nombre),
    ALORS ce n’est PAS du small talk.

========================================
2 - PERIOD_SUMMARY
========================================
----------------------------------------
DÉCLENCHEMENT
----------------------------------------

Si la question contient une demande de bilan / résumé / récapitulatif,
par exemple :
- "bilan"
- "résumé" / "resume"
- "récap" / "recap"
- "synthèse" / "synthese"
- "vue d’ensemble" / "vue d'ensemble"

tu dois retourner l’intent PERIOD_SUMMARY.

========================================
3 - COACHING
========================================
Utilise l’intent COACHING si l’utilisateur :
- parle de régularité, progression, charge, cohérence
- La question est souvent une question ouverte

========================================
4 - GET_METRIC
========================================
L'intent GET_METRIC est utilisé pour récupérer une métrique spécifique
sur une période donnée.
Exemples de questions déclenchant cet intent :
- "Quelle distance ai-je couru cette semaine ?"
- "Combien de séances ai-je faites le mois dernier ?"
Retourne EXACTEMENT :
{
  "intent": "GET_METRIC",
  "metric": "<METRIC>",
  "period": "<PERIOD>"
}


"""


def detect_intent(message: str) -> dict:
    raw = call_ollama(prompt=f"{SYSTEM_PROMPT}\n\nUser message:\n{message}")

    print("🟣 LLM RAW OUTPUT :", raw)

    intent = safe_json_load(raw)
    print("🟢 PARSED INTENT :", intent)

    intent["original_message"] = message
    return intent
