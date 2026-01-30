import re
from intent_based_querying.normalization.normalizer import normalize


QUESTION_WORDS = [
    "combien",
    "quel",
    "quelle",
    "quels",
    "quelles",
    "est-ce",
    "dois-je",
    "faut-il",
    "puis-je",
    "tu penses",
    "tu crois",
    "ça va",
    "c'est trop",
    "c'est normal",
    "comment",
    "pourquoi",
    "c'est quoi",
    "connais tu",
    "as tu",
    "connaissez vous",
    "avez vous",
]

RECOMMENDATION_VERBS = [
    "recommandation",
    "recommandations",
    "recommande",
    "recommander",
    "recommandes",
    "conseil",
    "conseilles",
    "que faire",
    "quoi faire",
    "comment m'entraîner",
]

ACTION_VERBS = [
    "fais",
    "fait",
    "donne",
    "montre",
    "résume",
    "resume",
    "bilan",
    "recap",
    "récap",
    "analyse",
    "analyse moi",
    "compare",
    "prépare",
    "recommande",
    "propose",
]

QUESTION_MARK = re.compile(r"\?")


def intent_gatekeeper(message: str) -> dict:
    msg = normalize(message)

    # 1️⃣ Recommandation explicite (PRIORITÉ HAUTE)
    for verb in RECOMMENDATION_VERBS:
        if re.search(rf"\b{re.escape(verb)}\b", msg):
            return {"intent_type": "RECOMMENDATION"}

    # 2️⃣ Question explicite
    if QUESTION_MARK.search(message):
        return {"intent_type": "QUESTION"}

    for word in QUESTION_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", msg):
            return {"intent_type": "QUESTION"}

    # 3️⃣ Action / impératif
    for verb in ACTION_VERBS:
        if re.search(rf"\b{re.escape(verb)}\b", msg):
            return {"intent_type": "ACTION"}

    # 4️⃣ Déclaration / contexte
    return {"intent_type": "NONE"}
