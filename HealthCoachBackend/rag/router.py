# rag/router.py

from typing import Optional, Dict, Any

from rag.models import (
    SemanticMatch,
    ExecutionPlan,
    FallbackSQLPlan,
)

# ---------------------------------------------------------
# PARAMÈTRES DE SEUIL (à ajuster plus tard)
# ---------------------------------------------------------

MIN_SIMILARITY = 0.80
MIN_CONFIDENCE = 0.80
MIN_DELTA = 0.05


# ---------------------------------------------------------
# Décision : accepte-t-on le match sémantique A ?
# ---------------------------------------------------------


def accept_semantic_match(match: SemanticMatch) -> bool:
    """
    Décide si un match issu du catalogue (A) est suffisamment fiable
    pour bypasser la détection d'intent classique.
    """
    if match.similarity < MIN_SIMILARITY:
        return False

    if match.confidence < MIN_CONFIDENCE:
        return False

    if match.delta_to_next < MIN_DELTA:
        return False

    return True


# ---------------------------------------------------------
# Pré-router principal (A → intent → B)
# ---------------------------------------------------------


class SemanticRouter:
    """
    Pré-router sémantique.
    - tente A (catalogue RAG)
    - sinon laisse la main au système existant
    - B sera branché plus tard
    """

    def __init__(self, catalog_retriever):
        """
        catalog_retriever doit exposer :
        - retrieve(message: str) -> Optional[SemanticMatch]
        """
        self.catalog_retriever = catalog_retriever

    def route(self, message: str) -> Optional[ExecutionPlan]:
        """
        Tente de produire un ExecutionPlan via A.
        Retourne None si A n'est pas concluant.
        """

        match: Optional[SemanticMatch] = self.catalog_retriever.retrieve(message)

        if match is None:
            return None

        if not accept_semantic_match(match):
            return ExecutionPlan(
                type="INTENT",
                intent=None,
                source="A",
                confidence=match.confidence,
                debug={
                    "reason": "semantic_match_rejected",
                    "similarity": match.similarity,
                    "delta_to_next": match.delta_to_next,
                },
            )

        # Match accepté → intent structuré
        intent: Dict[str, Any] = {
            "use_case": match.use_case,
            **match.slots,
        }

        return ExecutionPlan(
            type="INTENT",
            intent=intent,
            source="A",
            confidence=match.confidence,
            debug={
                "semantic_match": True,
                "similarity": match.similarity,
                "delta_to_next": match.delta_to_next,
            },
        )
