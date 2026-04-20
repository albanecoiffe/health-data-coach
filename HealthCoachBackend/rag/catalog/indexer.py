# rag/catalog/indexer.py

from typing import List
from langchain_core.documents import Document
from sqlalchemy import text

from rag.vector_store import VectorStore
from rag.catalog.registry import CATALOG_CASES


class CatalogIndexer:
    def __init__(self, connection_string: str):
        self.vector_store = VectorStore(
            connection_string=connection_string,
            collection_name="rag_use_cases",
        )

    def build_documents(self) -> List[Document]:
        return [
            Document(
                page_content=case.text,
                metadata={
                    "use_case": case.use_case,
                    "slots": case.slots,
                },
            )
            for case in CATALOG_CASES
        ]

    def index(self, overwrite: bool = False) -> None:
        documents = self.build_documents()

        if not documents:
            raise RuntimeError("Aucun cas à indexer")

        if overwrite:
            # On tente une suppression best-effort
            from sqlalchemy import create_engine, text

            engine = create_engine(self.vector_store.connection_string)
            with engine.begin() as conn:
                # Si les tables n'existent pas encore, on ignore
                conn.execute(
                    text(
                        """
                        DO $$
                        BEGIN
                            IF EXISTS (
                                SELECT 1 FROM information_schema.tables
                                WHERE table_name = 'langchain_pg_collection'
                            ) THEN
                                DELETE FROM langchain_pg_embedding
                                WHERE collection_id IN (
                                    SELECT uuid FROM langchain_pg_collection
                                    WHERE name = :name
                                );

                                DELETE FROM langchain_pg_collection
                                WHERE name = :name;
                            END IF;
                        END $$;
                        """
                    ),
                    {"name": self.vector_store.collection_name},
                )

        # 🔥 Création OU réindexation (crée les tables si absentes)
        self.vector_store.index_documents(documents)
