import json
from datetime import date, timedelta
from services.llm import call_ollama
import calendar
import json
from services.memory import get_memory, add_to_memory


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
7 - PAR DÉFAUT
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


def answer_with_snapshot(message: str, snapshot, session_id: str) -> str:
    history = get_memory(session_id)

    memory_text = ""
    if history:
        memory_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)

    prompt = f"""
Tu es un coach de course à pied humain et bienveillant.
Conversation récente (si elle existe) :
{memory_text}

RÈGLES :
- Small talk → réponse courte, empathique, naturelle
- Coaching → tu peux utiliser les données ci-dessous
- Ne répète PAS une salutation si la conversation est déjà entamée
- Ne redémarre PAS la conversation à zéro
- Ne poses PAS de question générique si le contexte est clair
- Ne fais AUCUN calcul
- Ne modifies AUCUN chiffre


DONNÉES :
- Distance : {snapshot.totals.distance_km}
- Séances : {snapshot.totals.sessions}
- Durée : {snapshot.totals.duration_min}
- Charge ratio : {snapshot.training_load.ratio if snapshot.training_load else "N/A"}

Question :
{message}

Réponds de manière cohérente avec la conversation précédente.
"""

    reply = call_ollama(prompt)

    add_to_memory(session_id, "user", message)
    add_to_memory(session_id, "assistant", reply)

    return reply


def factual_response(snapshot, metric: str) -> dict:
    start, end = format_period_for_display(snapshot.period.start, snapshot.period.end)

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


def format_period_for_display(start_iso: str, end_iso: str) -> tuple[str, str]:
    """
    start inclus
    end exclus → affichage end - 1 jour
    """
    start = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


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
- Tu n’emploies PAS de labels humains (pas "ce mois-ci", etc.)
- Tu parles UNIQUEMENT avec les dates fournies
- Tu ne fais AUCUN méta-commentaire
- Tu présentes toujours la comparaison en partant de la période la plus récente
- Tu ne mentionnes jamais UP, DOWN ou STABLE dans le texte

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


def summary_response(snapshot) -> dict:
    start, end = format_period_for_display(snapshot.period.start, snapshot.period.end)

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

    # ❤️ Répartition cardiaque détaillée (EXISTANT — inchangé)
    zones_text = []
    zones = getattr(snapshot, "zones_percent", None)

    if isinstance(zones, dict) and zones:
        for z in ["z1", "z2", "z3", "z4", "z5"]:
            val = zones.get(z)
            if isinstance(val, (int, float)) and val > 0:
                zones_text.append(f"{z.upper()} : {round(val * 100)}%")

    zones_str = ", ".join(zones_text) if zones_text else "non disponibles"

    # 🔥 / 🟢 Intensité (AJOUT)
    if isinstance(zones, dict) and zones:
        low_intensity = zones.get("z1", 0) + zones.get("z2", 0) + zones.get("z3", 0)
        high_intensity = zones.get("z4", 0) + zones.get("z5", 0)

        if low_intensity + high_intensity > 0:
            low_str = f"{round(low_intensity * 100)}%"
            high_str = f"{round(high_intensity * 100)}%"
        else:
            low_str = "non disponibles"
            high_str = "non disponibles"
    else:
        low_str = "non disponibles"
        high_str = "non disponibles"

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
            f"🔥 Haute intensité (Z4–Z5) : {high_str}\n"
            f"🟢 Basse intensité (Z1–Z3) : {low_str}\n\n"
            f"🏅 Plus longue sortie : {longest_str}"
        )
    }


def get_distance(run):
    return getattr(run, "distance_km", None) or getattr(run, "distanceKm", None) or 0
