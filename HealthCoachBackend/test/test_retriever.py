import os
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))


load_dotenv()

DB = os.getenv("DATABASE_URL")
assert DB, "DATABASE_URL manquant"

from rag.catalog.retriever import CatalogRetriever

retriever = CatalogRetriever(connection_string=DB)

tests = [
    "combien de km cette semaine",
    "distance totale ce mois",
    "bilan de la semaine",
    "compare cette semaine avec la précédente",
    "est-ce que je progresse",
    "combien de mètres de dénivelé ce mois-ci",
    "combien de mètres de dénivelé sur les 4 dernières semaines",
    "dénivelé total des 3 derniers mois",
    "temps passé en zone 1 cette semaine",
    "temps en zone 2 ce mois-ci",
]

for q in tests:
    match = retriever.retrieve(q)
    print("\nQ:", q)
    if not match:
        print("  ❌ Aucun match")
    else:
        print(
            f"  → use_case={match.use_case} "
            f"slots={match.slots} "
            f"similarity={match.similarity:.3f} "
            f"conf={match.confidence:.3f} "
            f"delta={match.delta_to_next:.3f}"
        )
