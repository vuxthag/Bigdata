"""
data/pipeline/skills_config.py
================================
Centralised skill keyword configuration.
Edit this file to add / remove skills — no changes needed elsewhere.

Usage:
    from skills_config import SKILLS_LIST, build_skill_patterns
    patterns = build_skill_patterns()
"""
from __future__ import annotations

import re

# ── Master skill list ─────────────────────────────────────────────────────────
# Grouped by category for easy maintenance.
SKILLS_LIST: list[str] = [
    # ── Programming Languages ────────────────────────────────────────────────
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Golang",
    "Kotlin", "Swift", "Ruby", "PHP", "C++", "C#", "Rust", "Scala",
    "R", "Bash", "Shell", "Perl", "MATLAB", "Dart", "Elixir",

    # ── Web Frontend ─────────────────────────────────────────────────────────
    "React", "ReactJS", "Vue", "VueJS", "Angular", "Next.js", "Nuxt",
    "Svelte", "HTML", "CSS", "SCSS", "SASS", "Tailwind", "Bootstrap",
    "jQuery", "Webpack", "Vite",

    # ── Web Backend / Frameworks ─────────────────────────────────────────────
    "FastAPI", "Django", "Flask", "Express", "Spring Boot", "Laravel",
    "Node.js", "NestJS", "Rails", "ASP.NET", "Gin", "Fiber",

    # ── Mobile ───────────────────────────────────────────────────────────────
    "Flutter", "React Native", "SwiftUI", "Jetpack Compose",
    "Android", "iOS",

    # ── Databases ────────────────────────────────────────────────────────────
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
    "SQLite", "DynamoDB", "Cassandra", "Oracle", "MS SQL", "pgvector",
    "ClickHouse", "Neo4j",

    # ── Data / ML / AI ───────────────────────────────────────────────────────
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "TensorFlow", "PyTorch", "Keras", "scikit-learn", "Pandas", "NumPy",
    "Spark", "Hadoop", "Kafka", "Airflow", "dbt", "MLflow",
    "LangChain", "OpenAI", "Hugging Face", "BERT", "Transformer",
    "Data Science", "Big Data", "Data Engineering",
    "Power BI", "Tableau", "Looker", "Metabase",

    # ── Cloud & DevOps ───────────────────────────────────────────────────────
    "AWS", "Azure", "GCP", "Google Cloud",
    "Docker", "Kubernetes", "Terraform", "Helm",
    "CI/CD", "Jenkins", "GitHub Actions", "GitLab CI", "Ansible",
    "Linux", "Nginx", "Apache",

    # ── Architecture / Patterns ──────────────────────────────────────────────
    "Microservices", "REST", "GraphQL", "gRPC", "WebSocket",
    "Event-Driven", "Domain-Driven Design", "Clean Architecture",

    # ── Tools ────────────────────────────────────────────────────────────────
    "Git", "Jira", "Confluence", "Postman", "Figma",
    "RabbitMQ", "Celery",

    # ── Soft Skills ──────────────────────────────────────────────────────────
    "Agile", "Scrum", "Kanban", "Leadership", "Communication",
    "Problem Solving", "Team Work",
]


def build_skill_patterns() -> list[re.Pattern]:
    """
    Compile SKILLS_LIST into a list of case-insensitive word-boundary regex patterns.
    Call once at module load — patterns are reused across all jobs.
    """
    patterns: list[tuple[str, re.Pattern]] = []
    for skill in SKILLS_LIST:
        # Use word boundaries; escape so dots/+ in names are treated literally
        escaped = re.escape(skill)
        pattern = re.compile(r"\b" + escaped + r"\b", re.IGNORECASE)
        patterns.append((skill, pattern))
    return patterns


# Pre-compiled patterns — import this directly for performance
SKILL_PATTERNS: list[tuple[str, re.Pattern]] = build_skill_patterns()
