import json
from datetime import date, timedelta
from services.llm import call_ollama
import calendar
import json


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
5 - ANSWER_NOW FACTUEL
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
6 - PAR DÉFAUT
========================================

Retourne :
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
7 - COMPARAISONS (PRIORITÉ HAUTE)
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

========================================
8 - BIS — BILAN / RÉSUMÉ (PRIORITÉ HAUTE)
========================================

Si la question contient une demande de synthèse globale,
par exemple les mots :

- "bilan"
- "résumé"
- "resume"
- "récap"
- "recap"
- "synthèse"
- "synthese"
- "vue d’ensemble"
- "vue d'ensemble"

ALORS tu DOIS retourner EXACTEMENT :

{{
        "type": "SUMMARY"
}}

RÈGLES ABSOLUES :
- Tu ne retournes PAS de metric
- Tu ne retournes PAS d’offset
- Tu ne demandes PAS de snapshot
- Tu ne retournes PAS ANSWER_NOW
- Tu ne fais AUCUNE supposition sur la période


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


def answer_with_snapshot(message: str, snapshot) -> str:
    prompt = f"""
Tu es un coach de course à pied humain et bienveillant.

RÈGLES :
- Small talk → réponse courte, aucune statistique
- Coaching → tu peux utiliser les données ci-dessous
- Ne fais AUCUN calcul
- Ne modifies AUCUN chiffre

DONNÉES :
- Distance : {snapshot.totals.distance_km}
- Séances : {snapshot.totals.sessions}
- Durée : {snapshot.totals.duration_min}
- Charge ratio : {snapshot.training_load.ratio if snapshot.training_load else "N/A"}

Question :
{message}
"""
    return call_ollama(prompt)


def factual_response(snapshot, metric: str) -> dict:
    start = snapshot.period.start
    end = snapshot.period.end

    # Aucune séance
    if snapshot.totals.sessions == 0:
        return {
            "reply": f"Aucune séance enregistrée sur la période du {start} au {end}."
        }

    metric = metric.upper()

    if metric == "DISTANCE":
        return {
            "reply": (
                f"Sur la période du {start} au {end}, "
                f"tu as couru {round(snapshot.totals.distance_km, 1)} km."
            )
        }

    if metric == "DURATION":
        minutes = round(snapshot.totals.duration_min)
        hours = minutes // 60
        mins = minutes % 60

        if hours > 0:
            return {
                "reply": (
                    f"Sur la période du {start} au {end}, "
                    f"tu as couru pendant {hours}h{mins:02d}."
                )
            }
        else:
            return {
                "reply": (
                    f"Sur la période du {start} au {end}, "
                    f"tu as couru pendant {minutes} minutes."
                )
            }

    if metric == "SESSIONS":
        return {
            "reply": (
                f"Sur la période du {start} au {end}, "
                f"tu as effectué {snapshot.totals.sessions} séances."
            )
        }

    # Fallback propre
    return {
        "reply": (
            f"Sur la période du {start} au {end}, "
            f"tu as {snapshot.totals.sessions} séances pour "
            f"{round(snapshot.totals.distance_km, 1)} km."
        )
    }


def safe_parse_json(raw: str) -> dict | None:
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return None


def comparison_response_agent(
    message: str,
    metric: str,
    delta: dict,
    left_label: str,
    right_label: str,
) -> str:
    prompt = f"""
Tu es un coach de course à pied clair, précis et fiable.

Tu analyses une COMPARAISON entre deux périodes :
{left_label} vs {right_label}

Tu disposes UNIQUEMENT des écarts suivants (ce ne sont PAS des totaux) :
- Distance : {delta["distance_km"]} km
- Durée : {delta["duration_min"]} minutes
- Séances : {delta["sessions"]}

INTERPRÉTATION DES CHIFFRES :
- Valeur positive → PLUS
- Valeur négative → MOINS
- Valeur proche de zéro → STABLE

RÈGLES ABSOLUES :
- Tu n’inventes AUCUN chiffre
- Tu n’arrondis PAS autrement que ce qui est fourni
- Tu n’expliques PAS comment les chiffres sont calculés
- Tu ne fais AUCUNE supposition
- Tu n’emploies JAMAIS une formulation contradictoire
  (ex: "moins de temps" si la durée est positive)

ADAPTATION À LA QUESTION :
- Si la question est une QUESTION FERMÉE (oui / non),
  commence par "Oui" ou "Non", puis explique.
- Si la question est une DEMANDE DE COMPARAISON,
  commence par un CONSTAT GLOBAL, sans "oui" ni "non".

STRUCTURE GÉNÉRALE :
- 1 phrase de réponse principale adaptée à la question
- 1 phrase qui précise distance, durée et séances

EXEMPLES À SUIVRE STRICTEMENT :

Exemple A — Question fermée :
Question : "Ai-je couru plus cette semaine que la semaine dernière ?"
Distance = +5 km, Durée = +30 min, Séances = +1
→
"Oui, tu as couru davantage. Tu as parcouru environ 5 km de plus, passé 30 minutes supplémentaires à courir et ajouté une séance."

Exemple B — Question fermée :
Distance = -3 km, Durée = -20 min, Séances = -1
→
"Non, ton volume est un peu plus bas. Tu as couru environ 3 km de moins, passé 20 minutes de moins à courir et fait une séance en moins."

Exemple C — Demande de comparaison :
Question : "Compare ce mois avec le mois dernier"
Distance = -95.9 km, Durée = -634 min, Séances = -12
→
"Ce mois-ci, ton volume est nettement plus bas. Tu as couru environ 95.9 km de moins, passé 634 minutes de moins à courir et effectué 12 séances en moins."

Exemple D — Situation stable :
Distance = +0.5 km, Durée = +2 min, Séances = 0
→
"C’est très proche de la période précédente, avec seulement un léger surplus de distance et de temps, et un nombre de séances identique."

QUESTION UTILISATEUR :
"{message}"
"""
    return call_ollama(prompt)


def summary_response(snapshot) -> dict:
    start = snapshot.period.start
    end = snapshot.period.end

    if snapshot.totals.sessions == 0:
        return {
            "reply": f"Aucune séance enregistrée sur la période du {start} au {end}."
        }

    distance = round(snapshot.totals.distance_km, 1)
    duration_min = round(snapshot.totals.duration_min)
    hours = duration_min // 60
    minutes = duration_min % 60
    sessions = snapshot.totals.sessions
    elevation = round(snapshot.totals.elevation_m)

    # ❤️ Zones cardiaques
    zones_text = []
    zones = getattr(snapshot, "zones_percent", None)

    if isinstance(zones, dict) and zones:
        for z in ["z1", "z2", "z3", "z4", "z5"]:
            val = zones.get(z)
            if isinstance(val, (int, float)) and val > 0:
                zones_text.append(f"{z.upper()} : {round(val * 100)}%")

    zones_str = ", ".join(zones_text) if zones_text else "non disponibles"

    # 🏅 Plus longue sortie
    longest = getattr(snapshot, "longest_run_km", None)

    longest_str = (
        f"{round(longest, 1)} km"
        if isinstance(longest, (int, float)) and longest > 0
        else "non disponible"
    )

    return {
        "reply": (
            f"📊 Bilan de la période {start} → {end}\n\n"
            f"🏃 Distance totale : {distance} km\n"
            f"⏱️ Temps total : {hours}h{minutes:02d}\n"
            f"📆 Séances : {sessions}\n"
            f"⛰️ D+ : {elevation} m\n\n"
            f"❤️ Répartition cardiaque : {zones_str}\n"
            f"🏅 Plus longue sortie : {longest_str}"
        )
    }


def get_distance(run):
    return getattr(run, "distance_km", None) or getattr(run, "distanceKm", None) or 0
