"""
preprocessing.py
================
Text cleaning utilities.

Chức năng:
- lowercase
- remove URL
- remove special characters
- normalize text (whitespace)
"""

from __future__ import annotations

import re


_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", flags=re.IGNORECASE)
_NON_ALPHA_PATTERN = re.compile(r"[^a-z\s]+", flags=re.IGNORECASE)
_WHITESPACE_PATTERN = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """
    Clean and normalize input text for TF-IDF vectorization.

    Steps:
    - Lowercase
    - Remove URLs
    - Remove special characters (keep letters and whitespace)
    - Normalize whitespace

    Parameters
    ----------
    text:
        Input string.

    Returns
    -------
    str
        Cleaned string. If input is not a string, returns empty string.
    """
    if not isinstance(text, str):
        return ""

    text = text.lower()
    text = _URL_PATTERN.sub(" ", text)
    text = _NON_ALPHA_PATTERN.sub(" ", text)
    text = _WHITESPACE_PATTERN.sub(" ", text).strip()
    return text
