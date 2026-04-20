# Role : appeler le SemanticRouter (A)
# décider :	A → intent structuré
# sinon → fallback vers intent existant (plus tard)


from typing import Optional, Dict, Any

from rag.router import SemanticRouter
from rag.catalog.retriever import CatalogRetriever
from rag.models import ExecutionPlan


class SemanticEntrypoint:
    """
    Point d’entrée sémantique AVANT le router métier.
    """

    def __init__(self, connection_string: str):
        self.semantic_router = SemanticRouter(
            catalog_retriever=CatalogRetriever(connection_string=connection_string)
        )

    def resolve_intent(
        self,
        message: str,
        base_intent: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retourne un intent structuré compatible avec route_intent.
        """

        plan: Optional[ExecutionPlan] = self.semantic_router.route(message)

        # Cas A accepté
        if plan and plan.type == "INTENT" and plan.intent:
            intent = {
                "intent": plan.intent["use_case"],
                **plan.intent,
                "period": plan.intent.get("period"),
                "original_message": message,
                "_source": "semantic_A",
                "_confidence": plan.confidence,
            }
            return intent

        # Fallback : intent existant (LLM / rules)
        if base_intent:
            base_intent["_source"] = "legacy_intent"
            return base_intent

        # Rien trouvé
        return {
            "intent": "SMALL_TALK",
            "original_message": message,
            "_source": "fallback_default",
        }
