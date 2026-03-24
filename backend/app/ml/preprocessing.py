"""
ml/preprocessing.py
====================
Text cleaning utilities (migrated from src/preprocessing.py).
Extended to better handle CV and job description text.
"""
from __future__ import annotations

import re

# ── Compiled regex patterns ───────────────────────────────────────────────────
_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", flags=re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"\S+@\S+\.\S+")
_PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-().]{7,}\d")
_NON_ALPHA_PATTERN = re.compile(r"[^a-z\s]+", flags=re.IGNORECASE)
_WHITESPACE_PATTERN = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """
    Clean and normalize input text for SBERT encoding.

    Steps:
    - Lowercase
    - Remove URLs, emails, phone numbers
    - Remove special characters (keep letters and whitespace)
    - Normalize whitespace

    Parameters
    ----------
    text : str
        Input string.

    Returns
    -------
    str
        Cleaned string. Returns empty string for non-string input.
    """
    if not isinstance(text, str):
        return ""

    text = text.lower()
    text = _URL_PATTERN.sub(" ", text)
    text = _EMAIL_PATTERN.sub(" ", text)
    text = _PHONE_PATTERN.sub(" ", text)
    text = _NON_ALPHA_PATTERN.sub(" ", text)
    text = _WHITESPACE_PATTERN.sub(" ", text).strip()
    return text
