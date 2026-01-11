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

    scores = {
        "REGULARITY": score_category(stems, REGULARITY_STRONG, REGULARITY_WEAK),
        "LOAD": score_category(stems, LOAD_STRONG, LOAD_WEAK),
        "VOLUME": score_category(stems, VOLUME_STRONG, VOLUME_WEAK),
    }

    if DEBUG_COACHING:
        print("📊 Scores détaillés :")
        for k, v in scores.items():
            print(f"   - {k:<10} → {v}")

    # ======================================================
    # 🔒 CONTEXTE SPORT (sauf régularité)
    # ======================================================
    has_sport_context = bool(stems & SPORT_CONTEXT)
    has_regularity_hint = bool(stems & REGULARITY_STRONG)

    if DEBUG_COACHING:
        print("🏃 Sport context :", has_sport_context)
        print("📊 Regularity hint :", has_regularity_hint)

    # ======================================================
    # 🔒 FILTRE CONTEXTE — INTELLIGENT
    # ======================================================

    has_strong_signal = (
        (stems & REGULARITY_STRONG) or (stems & LOAD_STRONG) or (stems & VOLUME_STRONG)
    )

    if DEBUG_COACHING:
        print("💡 Strong signal détecté :", bool(has_strong_signal))

    # On bloque UNIQUEMENT si :
    # - aucun mot fort métier
    # - ET aucun contexte sport
    if not has_strong_signal and not has_sport_context:
        if DEBUG_COACHING:
            print("⛔ Aucun signal métier ni contexte sport → abandon")
        return None

    # ======================================================
    # 🥇 PRIORITÉ MÉTIER
    # ======================================================
    if scores["LOAD"] > 0:
        if DEBUG_COACHING:
            print("✅ Type retenu : LOAD (priorité métier)")
        return "LOAD"

    if scores["REGULARITY"] > 0:
        if DEBUG_COACHING:
            print("✅ Type retenu : REGULARITY")
        return "REGULARITY"

    if scores["VOLUME"] > 0:
        if DEBUG_COACHING:
            print("✅ Type retenu : VOLUME")
        return "VOLUME"

    if DEBUG_COACHING:
        print("⚠️ Aucun type détecté malgré le scoring")

    return None
