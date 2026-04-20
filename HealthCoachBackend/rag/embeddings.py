# rag/embeddings.py

from typing import List
import numpy as np
import requests


class EmbeddingClient:
    """
    Client d'embeddings basé sur Ollama (local, gratuit).
    """

    def __init__(
        self,
        model_name: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
    ):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    # -----------------------------------------------------

    def embed(self, text: str) -> np.ndarray:
        """
        Génère un embedding normalisé via Ollama.
        """

        if not text or not text.strip():
            raise ValueError("Impossible de générer un embedding pour un texte vide")

        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={
                "model": self.model_name,
                "prompt": text,
            },
            timeout=30,
        )

        response.raise_for_status()

        vector: List[float] = response.json()["embedding"]

        embedding = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(embedding)

        if norm == 0.0:
            return embedding

        # Normalisation → cosine similarity = dot product
        return embedding / norm
