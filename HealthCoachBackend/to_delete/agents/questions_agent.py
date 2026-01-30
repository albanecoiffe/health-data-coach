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

DATE DU JOUR

Si la question demande explicitement :
- "quel jour sommes-nous"
- "quelle est la date"
- "on est quel jour"
- "date du jour"

ALORS retourne STRICTEMENT :
{{
        "type": "ANSWER_NOW",
  "answer_mode": "SMALL_TALK"
}}

========================================
2 - CHANGEMENT DE PÉRIODE — SEMAINES
========================================
Si la question contient une référence à une semaine RELATIVE
(par rapport à aujourd’hui), tu DOIS utiliser REQUEST_WEEK.

Si la question contient :
- "la semaine dernière"
- "semaine dernière"
→ offset = -1

Si la question contient :
- "il y a X semaines"
- "il y a X semaine"
→ offset = -X

Retourne :
{{
  "type": "REQUEST_WEEK",
  "offset": -X,
  "metric": "<métrique détectée>"
}}

 Même si la question parle de km, durée, séances, etc.

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

Cette règle ne s’applique PAS
si la question contient une comparaison.

========================================
3 - CHANGEMENT DE PÉRIODE — MOIS RELATIFS
========================================
(APPLICABLE UNIQUEMENT SI LE MOT "mois" EST PRÉSENT)

FORMAT OBLIGATOIRE POUR LES MOIS :
{{
        "month_offset": <entier négatif ou zéro>
}}

Si la question contient EXACTEMENT :
- "ce mois"
- "ce mois-ci"

Retourne :
{{
        "type": "REQUEST_MONTH_RELATIVE",
  "month_offset": 0,
  "metric": "<metric détectée>"
}}

Si la question contient EXACTEMENT :
- "le mois dernier"
- "mois dernier"

Retourne :
{{
        "type": "REQUEST_MONTH_RELATIVE",
  "month_offset": -1,
  "metric": "<metric détectée>"
}}

Si la question contient :
- "il y a X mois"

Retourne :
{{
        "type": "REQUEST_MONTH_RELATIVE",
  "month_offset": -X,
  "metric": "<metric détectée>"
}}

INTERDIT ABSOLUMENT POUR LES MOIS :
- utiliser "offset"
- utiliser CURRENT_MONTH / PREVIOUS_MONTH

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

INTERDIT ABSOLUMENT :
- REQUEST_MONTH_RELATIVE
- month_offset

Exemple : 
"Quel est mon volume de course en novembre 2023 ?"
{{
  "type": "REQUEST_MONTH",
  "month": 11,
  "year": 2023,
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
  "year_offset": -1,
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
  "year_offset": -X,
  "metric": "<métrique détectée>"
}}

Exemples :
- "l'année dernière" → {{"year_offset": -1 }}
- "il y a 3 ans"     → {{"year_offset": -3 }}
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

RÈGLE CRITIQUE :

- "il y a X semaines" → TOUJOURS REQUEST_WEEK
- "il y a X mois"     → REQUEST_MONTH_RELATIVE
- "il y a X ans"      → REQUEST_YEAR_RELATIVE

L’unité temporelle explicite a TOUJOURS priorité
sur toute autre règle.

========================================
9 - PROFIL / HABITUDES LONG TERME (PRIORITÉ ABSOLUE)
========================================

Si la question porte sur :
- régularité
- constance
- habitudes
- rythme global
- charge
- surcharge
- trop
- trop d'effort
- sur le long terme
- en général
- d'habitude

Exemples :
- "Est-ce que je suis régulier ?"
- "Est-ce que je cours souvent ?"
- "J’ai une routine stable ?"
- "Est-ce que je progesse"
- "Est ce que je suis en surcharge?"

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
- PROGRESS
- PROGRESSION

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
  "left": <période A>,
  "right": <période B>
}}

La décision COMPARE_PERIODS est PRIORITAIRE
sur toute autre règle temporelle.

----------------------------------------
RÈGLE CRITIQUE — SÉMANTIQUE LEFT / RIGHT
----------------------------------------

Dans toute décision COMPARE_PERIODS :

- "left" représente TOUJOURS la période de référence,
  la plus récente ou celle nommée en premier.

- "right" représente TOUJOURS la période de comparaison,
  plus ancienne ou utilisée comme base de comparaison.

INTERPRÉTATION OBLIGATOIRE :

- "ce mois"        → left  = {{ "month_offset": 0 }}
- "le mois dernier" → right = {{ "month_offset": -1 }}

- "cette semaine"        → left  = {{ "offset": 0 }}
- "la semaine dernière"  → right = {{ "offset": -1 }}
- "l’année dernière" → left = {{ "year_offset": -1 }}
- "il y a 2 ans"     → right = {{ "year_offset": -2 }}

Il est STRICTEMENT INTERDIT :
- d’inverser left et right
- de laisser left ou right vide
- de retourner un objet vide {{}}
- left et right DOIVENT être présents
- left et right DOIVENT contenir exactement UN champ temporel

----------------------------------------
RÈGLE ABSOLUE — SEMAINES (CRITIQUE)
----------------------------------------

Pour TOUTE comparaison impliquant des semaines,
tu DOIS utiliser EXCLUSIVEMENT des offsets numériques.

FORMAT OBLIGATOIRE POUR LES SEMAINES :
{{
        "offset": <entier négatif ou zéro>
}}

INTERDIT ABSOLUMENT :
- strings ("CURRENT_WEEK", "PREVIOUS_WEEK", etc.)
- périodes glissantes
- objets avec "unit"
- noms inventés

----------------------------------------
RÈGLE — MOIS (STANDARD)
----------------------------------------

Pour toute comparaison impliquant des mois,
tu DOIS utiliser EXCLUSIVEMENT des month_offset.

FORMAT OBLIGATOIRE POUR LES MOIS :
{{
        "month_offset": <entier négatif ou zéro>
}}

INTERDIT ABSOLUMENT :
- utiliser "offset"
- strings ("CURRENT_MONTH", "PREVIOUS_MONTH", etc.)

----------------------------------------
RÈGLE — ANNÉES (STANDARD)
----------------------------------------

Pour toute comparaison impliquant des années,
tu DOIS utiliser EXCLUSIVEMENT des year_offset.

FORMAT OBLIGATOIRE POUR LES ANNÉES :
{{
        "year_offset": <entier négatif>
}}

INTERDIT ABSOLUMENT :
- utiliser "offset"
- strings ("YEAR_2025", etc.)

----------------------------------------
EXEMPLES DE COMPARAISONS VALIDES
----------------------------------------
" Ai-je couru plus la semaine dernière que il y a 3 semaines ? "
{{
        "type": "COMPARE_PERIODS",
  "metric": "DISTANCE",
  "left":  {{"offset": -1 }},
  "right": {{"offset": -3 }}
}}

"Compare ce mois avec le mois dernier"
{{
        "type": "COMPARE_PERIODS",
  "metric": "<metric>",
  "left":  {{"month_offset": 0 }},
  "right": {{"month_offset": -1 }}
}}

"Compare l'année dernière avec il y a 2 ans"
{{
        "type": "COMPARE_PERIODS",
  "metric": "<metric>",
  "left":  {{"year_offset": -1 }},
  "right": {{"year_offset": -2 }}
}}

========================================
9 - BILAN / RÉSUMÉ (PRIORITÉ ABSOLUE)
========================================

Cette règle a PRIORITÉ sur TOUTES les autres règles du prompt.

----------------------------------------
DISTINCTION FONDAMENTALE (CRITIQUE)
----------------------------------------

- Le champ "type" décrit TOUJOURS la PÉRIODE demandée.
- Le fait qu’une réponse soit un bilan / résumé est géré EXCLUSIVEMENT
  par le BACKEND via le champ "reply_mode": "SUMMARY".
- Le LLM ne doit JAMAIS produire "reply_mode".

CONSÉQUENCE DIRECTE :

- "type": "SUMMARY" est autorisé UNIQUEMENT
  s’il n’existe ABSOLUMENT AUCUNE période dans la question.
- Si UNE période est mentionnée (semaine, mois, année),
  retourner "type": "SUMMARY" est STRICTEMENT INTERDIT.

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

Tu DOIS appliquer les règles ci-dessous.

----------------------------------------
ÉTAPE 1 — DÉTECTION DE PÉRIODE (OBLIGATOIRE)
----------------------------------------

Analyse la question et détermine s’il existe UNE période explicite.

Périodes possibles :

- Semaine
  (ex: "cette semaine", "la semaine dernière", "il y a 2 semaines")
  → REQUEST_WEEK

- Mois relatif
  (ex: "ce mois", "le mois dernier", "il y a 3 mois")
  → REQUEST_MONTH_RELATIVE

- Mois nommé
  (ex: "novembre", "mars")
  → REQUEST_MONTH

- Année explicite
  (ex: "2025", "2024")
  → REQUEST_YEAR

- Année relative
  (ex: "l’année dernière", "il y a 2 ans")
  → REQUEST_YEAR_RELATIVE

----------------------------------------
ÉTAPE 2 — DÉCISION À RETOURNER
----------------------------------------

CAS A — AU MOINS UNE PÉRIODE EST DÉTECTÉE :

Tu DOIS retourner UNIQUEMENT une décision REQUEST_*
correspondant à LA période la plus précise mentionnée.

RÈGLES ABSOLUES DANS CE CAS :
- INTERDIT de retourner {{"type": "SUMMARY" }}
- INTERDIT de retourner ANSWER_NOW
- INTERDIT d’inclure "reply_mode"
- INTERDIT d’inclure plusieurs périodes
- Tu retournes UNE seule période

EXEMPLES CORRECTS :

"Bilan de la semaine dernière" →
{{
        "type": "REQUEST_WEEK",
  "offset": -1
}}

"Bilan de novembre" →
{{
        "type": "REQUEST_MONTH",
  "month": 11,
  "year": null
}}

"Résumé du mois dernier" →
{{
        "type": "REQUEST_MONTH_RELATIVE",
  "month_offset": -1
}}

"Fais moi un bilan de l’année 2025" →
{{
        "type": "REQUEST_YEAR",
  "year": 2025
}}

EXEMPLES INTERDITS (ERREURS) :

"Fais moi un bilan de l’année 2025"
FAUX: {{"type": "SUMMARY" }}

"Résumé du mois de novembre"
FAUX: {{"type": "SUMMARY" }}

----------------------------------------
CAS B — AUCUNE PÉRIODE N’EST DÉTECTÉE :
----------------------------------------

Tu DOIS retourner STRICTEMENT :

{{
        "type": "SUMMARY"
}}

RÈGLES ABSOLUES DANS CE CAS :
- SUMMARY ne contient JAMAIS :
  - metric
  - year
  - offset
  - month_offset
  - year_offset
- SUMMARY est réservé UNIQUEMENT
  aux bilans globaux SANS période

----------------------------------------
RÈGLE FINALE (NON NÉGOCIABLE)
----------------------------------------
- Le mot "bilan", "résumé" ou "récap" n’est JAMAIS une période.
- Si une période est présente,
  "SUMMARY" est INTERDIT.
- Le "type" retourné DOIT toujours représenter
  la période réellement demandée par l’utilisateur.
----------------------------------------
AUTO-CONTRÔLE FINAL (OBLIGATOIRE)
----------------------------------------

AVANT de produire le JSON final, tu DOIS appliquer ce contrôle :

1 - La question contient-elle une période explicite ?
   (semaine, mois, année, date, nombre d’unités temporelles)

SI OUI :
- IL EST STRICTEMENT INTERDIT de retourner {{"type": "SUMMARY" }}
- Tu DOIS retourner un type REQUEST_* correspondant à la période

2 - La question ne contient AUCUNE période :
- ALORS et SEULEMENT ALORS tu peux retourner {{"type": "SUMMARY" }}

----------------------------------------
VÉRIFICATION FINALE (NON NÉGOCIABLE)
----------------------------------------

Si le JSON final contient :
{{"type": "SUMMARY" }}
ALORS la question NE DOIT contenir :
- AUCUN mois
- AUCUNE semaine
- AUCUNE année
- AUCUNE expression temporelle

SI CE N’EST PAS LE CAS :
→ LE JSON EST FAUX
→ TU DOIS LE CORRIGER AVANT DE RÉPONDRE

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
