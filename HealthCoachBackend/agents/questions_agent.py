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


def analyze_question(message: str, current_period: tuple[str, str]) -> dict:
    start, end = current_period
    print("\n================= ANALYZE_QUESTION =================")
    print("📝 MESSAGE UTILISATEUR :", repr(message))
    print("📅 PÉRIODE COURANTE   :", start, "→", end)

    prompt = f"""
Tu es un moteur de décision STRICT pour une application de suivi de course à pied.

Tu dois retourner UNE décision JSON valide, et RIEN d'autre.

========================================
1 - PRIORITÉ ABSOLUE — SMALL TALK
========================================

- Si le message est une salutation ou une phrase vague
    (ex: "hello", "salut", "bonjour", "ça va", "merci", "ok") :

Retourne EXACTEMENT :
{{
  "type": "ANSWER_NOW",
  "answer_mode": "SMALL_TALK"
}}

- Tu n’as PAS le droit de demander un snapshot dans ce cas.

- Si la phrase contient un indicateur quantitatif
    (distance, km, temps, durée, séance, nombre),
    ALORS ce n’est PAS du small talk.

========================================
2 - CHANGEMENT DE PÉRIODE — SEMAINES
========================================

Si la question contient :

- "semaine dernière" → offset = -1
- "il y a X semaines" → offset = -X

Retourne :
{{
  "type": "REQUEST_WEEK",
  "offset": -X,
  "metric": "<métrique détectée>"
}}

⚠️ Même si la question parle de km, durée, séances, etc.

----------------------------------------
SEMAINE COURANTE
----------------------------------------

Si la question contient exactement :
- "cette semaine"
- "la semaine actuelle"

Retourne :
{{
  "type": "ANSWER_NOW",
  "answer_mode": "FACTUAL",
  "metric": "<métrique détectée>"
}}

========================================
3 - CHANGEMENT DE PÉRIODE — MOIS RELATIFS (PRIORITÉ ABSOLUE)
========================================

Si la question contient EXACTEMENT :

- "ce mois-ci"
- "ce mois ci"

ALORS tu DOIS retourner EXACTEMENT :

{{
  "type": "REQUEST_MONTH_RELATIVE",
  "offset": 0,
  "metric": "<metric détectée>"
}}

Si la question contient EXACTEMENT :

- "le mois dernier"
- "mois dernier"

ALORS tu DOIS retourner EXACTEMENT :

{{
  "type": "REQUEST_MONTH_RELATIVE",
  "offset": -1,
  "metric": "<metric détectée>"
}}

Si la question contient :

- "il y a X mois"

ALORS tu DOIS retourner :

{{
  "type": "REQUEST_MONTH_RELATIVE",
  "offset": -X,
  "metric": "<metric détectée>"
}}

⚠️ Tu n’as PAS le droit :
- d’inverser les offsets
- de retourner REQUEST_WEEK
- de retourner ANSWER_NOW


========================================
4 - MOIS ABSOLU (EXPLICITE SEULEMENT)
========================================

Si (et seulement si) un mois explicite est mentionné
(janvier → décembre) :

Retourne :
{{
  "type": "REQUEST_MONTH",
  "month": 1-12,
  "year": YYYY ou null,
  "metric": "<métrique détectée>"
}}

========================================
5 - CHANGEMENT DE PÉRIODE — ANNÉES RELATIVES
========================================

Si la question contient EXACTEMENT :
- "l'année dernière"
- "annee derniere"
- "l’an dernier"
- "an dernier"
- "l’année passée"
- "annee passee"

ALORS tu DOIS retourner EXACTEMENT :
{{
  "type": "REQUEST_YEAR_RELATIVE",
  "offset": -1,
  "metric": "<métrique détectée>"
}}

Tu n’as PAS le droit :
- de retourner REQUEST_MONTH_RELATIVE
- de retourner REQUEST_MONTH
- de retourner REQUEST_WEEK

Si la question contient une expression du type :
- "il y a X ans"
- "il y a X années"
où X est un nombre entier strictement positif,

ALORS tu DOIS retourner EXACTEMENT :
{{
   "type": "REQUEST_YEAR_RELATIVE",
  "offset": -X,
  "metric": "<métrique détectée>"
}}

Exemples :
- "il y a 2 ans" → offset = -2
- "il y a 5 ans" → offset = -5
Tu n’as PAS le droit :
- de retourner REQUEST_MONTH_RELATIVE
- de retourner REQUEST_MONTH
- de retourner REQUEST_WEEK
- de retourner ANSWER_NOW

========================================
6 - ANSWER_NOW FACTUEL
========================================

Si la question demande une valeur mesurable
(distance, km, durée, temps, séances, FC, allure, dénivelé) :

Retourne :
{{
  "type": "ANSWER_NOW",
  "answer_mode": "FACTUAL",
  "metric": "<métrique détectée>"
}}

========================================
9 - PROFIL / HABITUDES LONG TERME (PRIORITÉ ABSOLUE)
========================================

Si la question porte sur :
- régularité
- constance
- habitudes
- rythme global
- sur le long terme
- en général
- d'habitude

Exemples :
- "Est-ce que je suis régulier ?"
- "Est-ce que je cours souvent ?"
- "J’ai une routine stable ?"

Retourne STRICTEMENT :
{{
        "type": "ANSWER_NOW",
  "answer_mode": "COACHING"
}}

========================================
NORMALISATION DES MÉTRIQUES (OBLIGATOIRE)
========================================

Tu DOIS utiliser UNIQUEMENT les métriques suivantes :

- DISTANCE
- DURATION
- SESSIONS
- AVG_HR
- PACE
- ELEVATION
- LOAD
- UNKNOWN

INTERDIT ABSOLUMENT :
- TIME
- TEMPS
- HOURS
- MINUTES
- KMH
- SPEED

RÈGLE :
- "temps", "durée", "time", "heures", "minutes" → DURATION
- "km", "kilomètres", "distance" → DISTANCE
- "séances", "entraînements" → SESSIONS

Si tu n’es pas sûr → UNKNOWN

========================================
MÉTRIQUES POSSIBLES
========================================

DISTANCE | DURATION | SESSIONS | AVG_HR | PACE | ELEVATION | LOAD | UNKNOWN

========================================
8 - COMPARAISONS (PRIORITÉ HAUTE)
========================================

Si la question compare deux périodes
(ex: "plus que", "moins que", "autant que", "comparé à", "par rapport à") :

Retourne :
{{
  "type": "COMPARE_PERIODS",
  "metric": "<métrique détectée>",
  "left": "<période A>",
  "right": "<période B>"
}}

Exemples :

"Est-ce que j’ai couru plus que la semaine dernière ?"
→
{{
   "type": "COMPARE_PERIODS",
  "metric": "DISTANCE",
  "left": "CURRENT_WEEK",
  "right": "PREVIOUS_WEEK"
}}

"Est-ce que je fais plus de séances ce mois-ci ?"
→
{{
   "type": "COMPARE_PERIODS",
  "metric": "SESSIONS",
  "left": "CURRENT_MONTH",
  "right": "PREVIOUS_MONTH"
}}

Si la question contient :
- "ce mois par rapport au mois dernier"
→
{{
   "type": "COMPARE_PERIODS",
  "metric": "<metric>",
  "left": "CURRENT_MONTH",
  "right": "PREVIOUS_MONTH"
}}

Si la question contient :
- "les deux dernières semaines"
→
{{
        "type": "COMPARE_PERIODS",
  "metric": "<metric>",
  "left": "LAST_2_WEEKS",
  "right": "PREVIOUS_2_WEEKS"
}}

Si la question compare deux années explicites
(ex: "2025 avec 2024", "année 2023 par rapport à 2022") :

Retourne :
{{
  "type": "COMPARE_PERIODS",
  "metric": "<metric>",
  "left": "YEAR_2025",
  "right": "YEAR_2024"
}}


========================================
9 - BILAN / RÉSUMÉ (PRIORITÉ HAUTE)
========================================

Si la question contient une demande de synthèse globale avec:
- "bilan"
- "résumé"
- "resume"
- "récap"
- "recap"
- "synthèse"
- "synthese"
- "vue d’ensemble"
- "vue d'ensemble"

CAS 1 — une année explicite (YYYY) est mentionnée :
Retourne STRICTEMENT :
{{
        "type": "REQUEST_YEAR",
  "year": YYYY
}}

CAS 2 — aucune période explicite :
Retourne STRICTEMENT :
{{
        "type": "SUMMARY"
}}

RÈGLES ABSOLUES :
- SUMMARY ne contient JAMAIS de year
- SUMMARY ne contient JAMAIS d’offset
- Si une période est mentionnée, SUMMARY est INTERDIT
- Tu ne retournes JAMAIS SUMMARY avec une période


========================================
QUESTION
========================================
{message}

========================================
PÉRIODE COURANTE
========================================
{start} → {end}
"""

    raw = call_ollama(prompt)

    print("\n📥 RÉPONSE BRUTE DU LLM :")
    print(raw)

    try:
        data = safe_parse_json(raw)
        if not data or "type" not in data:
            print("⚠️ JSON non exploitable → fallback contrôlé")
            return {"type": "ANSWER_NOW", "answer_mode": "SMALL_TALK"}
        print("\n📦 JSON PARSÉ :", data)

        if not isinstance(data, dict) or "type" not in data:
            print("⚠️ JSON invalide → fallback SMALL_TALK")
            return {"type": "ANSWER_NOW", "answer_mode": "SMALL_TALK"}

        return data

    except Exception as e:
        print("❌ ERREUR JSON :", e)
        print("➡️ fallback SMALL_TALK")
        return {"type": "ANSWER_NOW", "answer_mode": "SMALL_TALK"}


def safe_parse_json(raw: str) -> dict | None:
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return None
