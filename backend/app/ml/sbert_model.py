"""
ml/sbert_model.py
==================
Sentence-BERT model wrapper replacing TF-IDF vectorizer.
Uses all-MiniLM-L6-v2 (22M params, 384-dim, fast inference on CPU).
"""
from __future__ import annotations

import os
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


class SBERTModel:
    """
    Wrapper around SentenceTransformer with checkpoint save/load support.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or settings.SBERT_MODEL_NAME
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the model on first access."""
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model

    @property
    def model_info(self) -> dict:
        return {
            "name": self._model_name,
            "embedding_dim": settings.EMBEDDING_DIM,
        }

    def encode(self, text: str) -> np.ndarray:
        """Encode a single text into a 384-dim embedding vector."""
        from app.ml.preprocessing import clean_text
        cleaned = clean_text(text)
        if not cleaned:
            return np.zeros(settings.EMBEDDING_DIM, dtype=np.float32)
        return self.model.encode(cleaned, normalize_embeddings=True)

    def encode_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Encode a list of texts in batches for efficiency."""
        from app.ml.preprocessing import clean_text
        cleaned = [clean_text(t) for t in texts]
        # Replace empty strings with placeholder to avoid errors
        cleaned = [t if t else "unknown" for t in cleaned]
        return self.model.encode(
            cleaned,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(cleaned) > 50,
        )

    def save_checkpoint(self, path: str) -> None:
        """Save the current model to disk."""
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        self.model.save(path)

    def load_checkpoint(self, path: str) -> None:
        """Load a model checkpoint from disk."""
        self._model = SentenceTransformer(path)
        self._model_name = path
