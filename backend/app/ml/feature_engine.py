"""
ml/feature_engine.py
=====================
Lightweight feature engineering for the AI ranking system.

Extracts structured signals from raw CV and job description text:
  - extract_skills()        → set[str]  (regex + curated tech-skill list)
  - years_of_experience()   → float     (regex: "N year(s)")
  - keyword_overlap()       → float     (Jaccard on token sets)
  - skill_overlap()         → float     (Jaccard on skill sets)
  - build_interaction_bonus() → float   (from user_interactions records)

Design goals:
  - Zero external NLP dependencies (pure stdlib + re)
  - Thread-safe (all functions are stateless)
  - Fast: O(n) on text length
"""
from __future__ import annotations

import re
from typing import Sequence

# ── Curated tech-skill vocabulary (~250 common terms) ────────────────────────
# Lower-cased. Matched as whole words (word-boundary regex).
_TECH_SKILLS: frozenset[str] = frozenset({
    # Languages
    "python", "javascript", "typescript", "java", "kotlin", "swift",
    "c", "c++", "c#", "go", "golang", "rust", "ruby", "php", "scala",
    "r", "matlab", "bash", "shell", "powershell", "sql", "plsql", "nosql",
    # Frontend
    "react", "vue", "angular", "svelte", "nextjs", "nuxtjs", "redux",
    "webpack", "vite", "tailwindcss", "bootstrap", "html", "css", "sass",
    "graphql", "rest", "restful",
    # Backend / frameworks
    "django", "flask", "fastapi", "spring", "springboot", "express",
    "nodejs", "nestjs", "laravel", "rails", "asp.net", "dotnet",
    # Databases
    "postgresql", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "oracle", "mssql", "neo4j", "influxdb",
    "clickhouse", "bigquery", "snowflake",
    # Cloud / DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform",
    "ansible", "jenkins", "github actions", "gitlab ci", "circleci",
    "nginx", "apache", "linux", "ubuntu", "centos",
    # Data / ML
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
    "spark", "hadoop", "airflow", "kafka", "dbt", "mlflow",
    "huggingface", "transformers", "bert", "llm", "openai",
    "xgboost", "lightgbm", "catboost", "nlp", "computer vision", "cv",
    # Methodologies
    "agile", "scrum", "kanban", "tdd", "bdd", "ci/cd", "devops",
    "microservices", "monolith", "serverless", "soa",
    # Tools
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "figma", "postman", "swagger", "openapi",
    # Soft (domain)
    "machine learning", "deep learning", "data science", "data engineering",
    "backend", "frontend", "fullstack", "full stack", "full-stack",
    "mobile", "ios", "android", "embedded", "firmware", "blockchain",
    "cybersecurity", "security", "devsecops",
})

# Pre-compiled patterns
_YOE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*\+?\s*(?:year|yr)s?\s*(?:of\s+)?(?:experience|exp)",
    re.IGNORECASE,
)
# Matches tech tokens: starts with letter, body is alphanum/+/#,
# special separator (./-)  must be followed by more alphanum — prevents
# trailing punctuation like "postgresql." from being captured as "postgresql."
_TOKEN_PATTERN = re.compile(
    r"[a-z][a-z0-9+#]*(?:[./\-][a-z0-9+#]+)*",
    re.IGNORECASE,
)


# ── Public API ────────────────────────────────────────────────────────────────

def extract_skills(text: str) -> set[str]:
    """
    Extract technical skills from free text.

    Strategy:
    1. Tokenise into lowercase words / short n-grams (1-2 tokens).
    2. Match against the curated _TECH_SKILLS vocabulary.

    Returns a set of matched skill strings (lower-cased).
    """
    if not text:
        return set()

    lower = text.lower()
    found: set[str] = set()

    # Single-word matches
    tokens = set(_TOKEN_PATTERN.findall(lower))
    found.update(tokens & _TECH_SKILLS)

    # Two-word bigram matches (e.g. "machine learning", "computer vision")
    words = lower.split()
    for i in range(len(words) - 1):
        bigram = f"{words[i]} {words[i+1]}"
        if bigram in _TECH_SKILLS:
            found.add(bigram)

    return found


def skill_overlap(cv_skills: set[str], jd_skills: set[str]) -> float:
    """
    Jaccard similarity between two skill sets.

    Returns 0.0 if both sets are empty; 1.0 for identical sets.
    """
    if not cv_skills and not jd_skills:
        return 0.0
    union = cv_skills | jd_skills
    if not union:
        return 0.0
    return len(cv_skills & jd_skills) / len(union)


def keyword_overlap(text_a: str, text_b: str, min_len: int = 4) -> float:
    """
    Token-level Jaccard similarity between two texts.

    Filters out tokens shorter than `min_len` to skip stop-words.
    """
    def tokenise(t: str) -> set[str]:
        return {tok.lower() for tok in _TOKEN_PATTERN.findall(t) if len(tok) >= min_len}

    set_a = tokenise(text_a)
    set_b = tokenise(text_b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def years_of_experience(text: str) -> float:
    """
    Extract the maximum years-of-experience figure mentioned in text.

    Recognises patterns like:
      "3 years of experience", "5+ years exp", "2.5 yr experience"

    Returns 0.0 if nothing is found.
    """
    matches = _YOE_PATTERN.findall(text or "")
    if not matches:
        return 0.0
    return max(float(m) for m in matches)


def build_interaction_bonus(
    interactions: Sequence[dict],
    target_job_id: str,
) -> float:
    """
    Compute an interaction bonus score for a specific job from a candidate's
    interaction history.

    Bonus weights (additive, clamped to [0, 1]):
      viewed   → +0.05
      saved    → +0.10
      applied  → +0.15   (strongest signal)
      skipped  → -0.05   (negative signal)

    Parameters
    ----------
    interactions : list of dicts with keys {job_id, action}
    target_job_id : str UUID of the job being scored

    Returns
    -------
    float in [0, 1]
    """
    _WEIGHTS = {
        "viewed":  0.05,
        "saved":   0.10,
        "applied": 0.15,
        "skipped": -0.05,
    }
    bonus = 0.0
    for ix in interactions:
        if str(ix.get("job_id", "")) == str(target_job_id):
            bonus += _WEIGHTS.get(str(ix.get("action", "")), 0.0)
    return float(max(0.0, min(1.0, bonus)))
