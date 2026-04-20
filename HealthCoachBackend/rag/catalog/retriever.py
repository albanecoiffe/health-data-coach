# rag/catalog/retriever.py

from typing import Optional, Dict, Any, List

from rag.models import SemanticMatch
from rag.vector_store import VectorStore


class CatalogRetriever:
    def __init__(self, connection_string: str, top_k: int = 3):
        self.top_k = top_k
        self.vector_store = VectorStore(
            connection_string=connection_string,
            collection_name="rag_use_cases",
        )

    def retrieve(self, message: str) -> Optional[SemanticMatch]:
        results: List[Dict[str, Any]] = self.vector_store.similarity_search(
            query=message,
            k=self.top_k,
        )

        if not results:
            return None

        top = results[0]
        second = results[1] if len(results) > 1 else None

        distance = top["score"]
        second_distance = second["score"] if second else 1.0

        similarity = 1.0 - distance
        delta = (1.0 - distance) - (1.0 - second_distance)

        metadata: Dict[str, Any] = top.get("metadata", {})

        use_case = metadata.get("use_case")
        if not use_case:
            # sécurité absolue : A ne doit jamais inventer
            return None

        slots = metadata.get("slots", {})

        return SemanticMatch(
            use_case=use_case,
            similarity=similarity,
            confidence=similarity,  # volontairement égal pour l’instant
            delta_to_next=delta,
            slots=slots,
        )
