# rag/models.py

from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal


# ---------------------------------------------------------
# Résultat du matching sémantique (Solution A)
# ---------------------------------------------------------


@dataclass
class SemanticMatch:
    """
    Résultat produit par le RAG catalogue (Solution A).
    Représente une intention POSSIBLE, avec un score.
    """

    use_case: str
    confidence: float
    slots: Dict[str, Any]

    # Scores utiles pour debug / seuil
    similarity: float
    delta_to_next: float

    def is_confident(self) -> bool:
        """
        Décision locale : est-ce que ce match est exploitable ?
        Le seuil exact sera décidé dans rag/router.py
        """
        return self.confidence >= 0.80


# ---------------------------------------------------------
# Plan SQL fallback (Solution B)
# ---------------------------------------------------------


@dataclass
class FallbackSQLPlan:
    """
    Plan d'exécution produit par le Text-to-SQL fallback (B).
    """

    sql: str
    confidence: float
    reason: str

    # Métadonnées de sécurité / debug
    tables: Optional[list[str]] = None
    limit: Optional[int] = None


# ---------------------------------------------------------
# 🧠 Plan d'exécution FINAL (unique point de sortie)
# ---------------------------------------------------------

ExecutionType = Literal["INTENT", "FALLBACK_SQL"]


@dataclass
class ExecutionPlan:
    """
    Objet unique renvoyé par le pré-router (A/B).
    C'est LE contrat avec le reste de l'application.
    """

    type: ExecutionType

    # Cas INTENT (chemin normal)
    intent: Optional[Dict[str, Any]] = None

    # Cas FALLBACK_SQL
    fallback_sql: Optional[FallbackSQLPlan] = None

    # Métadonnées globales
    source: Literal["A", "A+INTENT", "INTENT", "B"] = "INTENT"
    confidence: Optional[float] = None
    debug: Optional[Dict[str, Any]] = None
