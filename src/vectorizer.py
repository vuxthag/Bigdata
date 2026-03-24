"""
vectorizer.py
=============
TF-IDF vectorizer factory.

Yêu cầu:
- sử dụng TfidfVectorizer
- max_features = 5000
- remove English stopwords
"""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer


def build_vectorizer() -> TfidfVectorizer:
    """
    Build a configured TF-IDF vectorizer for job descriptions.

    Returns
    -------
    TfidfVectorizer
        Unfitted vectorizer with:
        - max_features=5000
        - stop_words='english'
    """
    return TfidfVectorizer(
        max_features=5000,
        stop_words="english",
    )
