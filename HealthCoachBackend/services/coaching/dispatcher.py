# services/coaching/dispatcher.py

from services.periods import normalize, lemmatize

# ======================================================
# 🧠 LEXIQUES (STEMS)
# ======================================================

# --- REGULARITY ---
REGULARITY_STRONG = {
    "regulier",
    "regul",
    "constanc",
    "constant",
    "const",
    "routin",
    "habitud",
    "stabl",
    "disciplin",
    "assidu",
    "continu",
    "souvent",
    "frequent",
    "entrain",
}

REGULARITY_WEAK = {
    "rythm",
    "frequenc",
    "souvent",
    "cadenc",
    "suivr",
    "mainten",
    "repeter",
    "systemat",
    "pratiqu",
}

# --- LOAD ---
LOAD_STRONG = {
    "surcharg",
    "surmenag",
    "epuis",
    "blessur",
    "cram",
    "overtrain",
}

LOAD_WEAK = {
    "charg",
    "fatigu",
    "intens",
    "exces",
    "trop",
    "dur",
    "lourd",
    "recup",
    "repos",
}

# --- VOLUME ---
VOLUME_STRONG = {
    "volum",
    "distanc",
    "kilometr",
    "km",
}

VOLUME_WEAK = {
    "long",
    "beaucoup",
    "augment",
    "hauss",
    "baisser",
    "diminu",
    "plus",
    "moins",
}

# --- CONTEXTE SPORTIF ---
SPORT_CONTEXT = {
    "cour",
    "entrain",
    "seanc",
    "run",
    "foot",
    "sort",
    "sport",
    "pratiqu",
}

PROGRESS_STRONG = {
    "progress",
    "progression",
    "support",
    "supporter",
    "toler",
    "tolerance",
    "mieux",
    "absorbe",
    "assimile",
    "encaisse",
    "sans_rupture",
    "ruptur",
    "evolu",
    "amelior",
}


# ======================================================
# ⚙️ DEBUG
# ======================================================
DEBUG_COACHING = True


# ======================================================
# 🔢 SCORING
# ======================================================
def score_category(stems: set, strong: set, weak: set) -> int:
    return 3 * len(stems & strong) + 1 * len(stems & weak)


# ======================================================
# 🧭 DÉTECTION DU TYPE DE COACHING
# ======================================================
def detect_coaching_type(message: str) -> str | None:
    msg = normalize(message)
    stems = set(lemmatize(msg))

    if DEBUG_COACHING:
        print("\n🧠 COACHING DETECTION")
        print("📝 Message brut :", message)
        print("🔎 Normalisé    :", msg)
        print("🌱 Stems        :", stems)

    # ======================================================
    # 📊 SCORING GLOBAL
    # ======================================================
    scores = {
        "PROGRESS": score_category(stems, PROGRESS_STRONG, set()),
        "LOAD": score_category(stems, LOAD_STRONG, LOAD_WEAK),
        "REGULARITY": score_category(stems, REGULARITY_STRONG, REGULARITY_WEAK),
        "VOLUME": score_category(stems, VOLUME_STRONG, VOLUME_WEAK),
    }

    if DEBUG_COACHING:
        print("📊 Scores détaillés :")
        for k, v in scores.items():
            print(f"   - {k:<10} → {v}")

    # ======================================================
    # 🔒 FILTRE CONTEXTE SPORT
    # - PROGRESS est AUTORISÉ sans contexte sport
    # ======================================================
    has_sport_context = bool(stems & SPORT_CONTEXT)

    if scores["PROGRESS"] == 0 and not has_sport_context and max(scores.values()) == 0:
        if DEBUG_COACHING:
            print("⛔ Aucun signal métier ni contexte sport → abandon")
        return None

    # ======================================================
    # 🥇 PRIORITÉ MÉTIER (ORDRE EXPLICITE)
    # ======================================================
    PRIORITY = ["PROGRESS", "LOAD", "REGULARITY", "VOLUME"]

    for key in PRIORITY:
        if scores[key] > 0:
            if DEBUG_COACHING:
                print(f"✅ Type retenu : {key}")
            return key

    if DEBUG_COACHING:
        print("⚠️ Aucun type détecté malgré le scoring")

    return None
