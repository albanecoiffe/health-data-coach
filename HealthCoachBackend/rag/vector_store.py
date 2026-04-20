# rag/vector_store.py

from typing import List, Dict, Any

from langchain_postgres import PGVector
from langchain_core.documents import Document

from rag.embeddings import EmbeddingClient


class VectorStore:
    """
    Wrapper pgvector (Neon) pour le RAG.
    Utilisé uniquement par A (catalogue) et B (Text-to-SQL).
    """

    def __init__(
        self,
        connection_string: str,
        collection_name: str = "rag_use_cases",
    ):
        if not connection_string:
            raise ValueError("connection_string est requis pour VectorStore")

        self.collection_name = collection_name
        self.connection_string = connection_string
        self.embedding_client = EmbeddingClient()

        # Adapter embeddings → format LangChain
        class _LCEmbeddingAdapter:
            def embed_documents(_, texts: List[str]) -> List[List[float]]:
                return [self.embedding_client.embed(t).tolist() for t in texts]

            def embed_query(_, text: str) -> List[float]:
                return self.embedding_client.embed(text).tolist()

        self.embeddings = _LCEmbeddingAdapter()

        # Lazy init
        self.store: PGVector | None = None

    # -------------------------------------------------
    # Initialisation lazy du store (RETRIEVAL)
    # -------------------------------------------------

    def _get_store(self) -> PGVector:
        if self.store is None:
            self.store = PGVector.from_existing_index(
                collection_name=self.collection_name,
                embedding=self.embeddings,
                connection=self.connection_string,
                distance_strategy="cosine",  # ✅ CRUCIAL
            )
        return self.store

    # -------------------------------------------------
    # INDEXATION
    # -------------------------------------------------

    def index_documents(self, docs: List[Document]) -> None:
        """
        Indexe des documents dans pgvector.
        À appeler au démarrage ou lors d’une migration.
        """
        if not docs:
            return

        PGVector.from_documents(
            documents=docs,
            embedding=self.embeddings,
            collection_name=self.collection_name,
            connection=self.connection_string,
            distance_strategy="cosine",  # ✅ CRUCIAL
        )

    # -------------------------------------------------
    # RETRIEVAL
    # -------------------------------------------------

    def similarity_search(
        self,
        query: str,
        k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Recherche sémantique par cosine similarity.
        Retourne documents + score.
        """
        store = self._get_store()

        results = store.similarity_search_with_score(query, k=k)

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
            }
            for doc, score in results
        ]
