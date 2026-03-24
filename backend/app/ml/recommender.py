"""
ml/recommender.py
=================
Pure numpy cosine similarity helpers (no DB dependency).
Used as fallback or for offline analysis.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def cosine_similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity matrix from L2-normalized embeddings.
    Since SBERT returns normalized vectors, this is just a dot product.

    Parameters
    ----------
    embeddings : np.ndarray — shape (n, 384), L2-normalized

    Returns
    -------
    np.ndarray — shape (n, n), similarity matrix
    """
    return np.dot(embeddings, embeddings.T)


def top_n_similar(
    query_vec: np.ndarray,
    corpus_vecs: np.ndarray,
    top_n: int = 5,
    exclude_indices: list[int] | None = None,
) -> list[tuple[int, float]]:
    """
    Find top-N most similar vectors in corpus_vecs to query_vec.

    Returns
    -------
    list of (index, similarity_score) tuples, sorted descending
    """
    scores = np.dot(corpus_vecs, query_vec)
    exclude = set(exclude_indices or [])

    indexed = [(i, float(s)) for i, s in enumerate(scores) if i not in exclude]
    indexed.sort(key=lambda x: x[1], reverse=True)
    return indexed[:top_n]
