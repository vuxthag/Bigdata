"""
services/embedding_service.py
==============================
Singleton Sentence-BERT service for encoding text to embeddings.
"""
from __future__ import annotations

from typing import List

import numpy as np

from app.ml.sbert_model import SBERTModel


class EmbeddingService:
    """
    Singleton wrapper around SBERTModel.
    Lazy-loads the model on first use to avoid blocking startup.
    """

    _instance: "EmbeddingService | None" = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = SBERTModel()
        return cls._instance

    def encode(self, text: str) -> np.ndarray:
        """Encode a single text into a 384-dim numpy vector."""
        return self._model.encode(text)

    def encode_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Batch encode texts for efficiency."""
        return self._model.encode_batch(texts, batch_size=batch_size)

    def compute_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Cosine similarity between two L2-normalized vectors.
        Since SBERT returns normalized vectors, dot product == cosine similarity.
        """
        score = float(np.dot(vec1, vec2))
        return max(0.0, min(1.0, score))  # clamp to [0, 1]

    def warm_up(self) -> None:
        """Pre-load the model by encoding a dummy sentence."""
        self._model.encode("warm up")

    @property
    def model(self) -> SBERTModel:
        return self._model


# Global singleton
embedding_service = EmbeddingService()
