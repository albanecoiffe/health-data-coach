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


def answer_with_snapshot(message: str, snapshot, session_id: str) -> str:
    history = get_memory(session_id)

    memory_text = ""
    if history:
        memory_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)

    signature = get_signature(session_id)

    signature_text = ""
    if signature:
        signature_text = f"""
    PROFIL LONG TERME DU COUREUR (12 derniers mois) :
    {json.dumps(signature.model_dump(), indent=2)}
    """

    print("\n🧠 SIGNATURE DEBUG")
    if signature:
        print(json.dumps(signature.model_dump(), indent=2))
    else:
        print("❌ Aucune signature pour cette session")

    prompt = f"""
Tu es un coach de course à pied humain, bienveillant et naturel.
Conversation récente (si elle existe) : {memory_text}
{signature_text}

━━━━━━━━━━━━━━━━━━━━━━
RÈGLES PRIORITAIRES (À RESPECTER AVANT TOUT)
━━━━━━━━━━━━━━━━━━━━━━

- Si le message utilisateur est une salutation simple
  (exemples : "hello", "salut", "bonjour", "hey", "ça va", "merci", "ok"),
  ALORS :
  - réponds brièvement et chaleureusement
  - NE COMMENTE AUCUNE donnée
  - NE PARLE PAS des chiffres, volumes, durées ou charges
  - NE POSE PAS de question liée à l’entraînement
  - une seule phrase suffit

- Tu ne dois commenter les données chiffrées
  QUE SI l’utilisateur pose explicitement une question
  sur son entraînement, sa charge, ses performances ou sa progression.

━━━━━━━━━━━━━━━━━━━━━━
RÈGLES GÉNÉRALES
━━━━━━━━━━━━━━━━━━━━━━

- Ne répète PAS une salutation si la conversation est déjà entamée
- Ne redémarre PAS la conversation à zéro
- Ne fais AUCUN calcul
- Ne modifies AUCUN chiffre
- Ne tires AUCUNE conclusion définitive
- Ton ton est calme, humain, non professoral

━━━━━━━━━━━━━━━━━━━━━━
DONNÉES PÉRIODE COURANTE
━━━━━━━━━━━━━━━━━━━━━━
(Ces données sont fournies UNIQUEMENT pour les questions de coaching)

- Distance : {snapshot.totals.distance_km} km
- Séances : {snapshot.totals.sessions}
- Durée : {snapshot.totals.duration_min} min
- Charge ratio : {snapshot.training_load.ratio if snapshot.training_load else "N/A"}

━━━━━━━━━━━━━━━━━━━━━━
MESSAGE UTILISATEUR
━━━━━━━━━━━━━━━━━━━━━━
{message}

Réponds de manière cohérente avec la conversation précédente.
"""

    reply = call_ollama(prompt)

    add_to_memory(session_id, "user", message)
    add_to_memory(session_id, "assistant", reply)

    return reply
