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

# ── Curated tech-skill vocabulary (~500 common terms) ────────────────────────
# Lower-cased. Matched as whole words (word-boundary regex).
_TECH_SKILLS: frozenset[str] = frozenset({
    # Programming Languages
    "python", "javascript", "typescript", "java", "kotlin", "swift",
    "c", "c++", "c#", "go", "golang", "rust", "ruby", "php", "scala",
    "r", "matlab", "bash", "shell", "powershell", "sql", "plsql", "nosql",
    "perl", "lua", "dart", "groovy", "haskell", "clojure", "erlang",
    "elixir", "julia", "objective-c", "objc", "vb.net", "vba", "apex",
    "solidity", "vyper", "rust",
    # Frontend
    "react", "vue", "vue.js", "angular", "svelte", "nextjs", "next.js",
    "nuxtjs", "nuxt.js", "redux", "mobx", "zustand", "recoil",
    "webpack", "vite", "rollup", "parcel", "esbuild",
    "tailwindcss", "tailwind", "bootstrap", "material-ui", "mui",
    "antd", "chakra-ui", "styled-components", "sass", "scss", "less",
    "html", "html5", "css", "css3", "canvas", "svg", "webgl", "three.js",
    "jquery", "backbone", "ember", "graphql", "apollo", "relay",
    "rest", "restful", "soap", "grpc", "websockets", "socket.io",
    "pwa", "service workers", "webassembly", "wasm",
    # Backend / Frameworks
    "django", "flask", "fastapi", "tornado", "celery", "aiohttp",
    "spring", "springboot", "spring boot", "spring cloud", "spring security",
    "express", "express.js", "nodejs", "node.js", "nest", "nestjs", "nest.js",
    "laravel", "symfony", "codeigniter", "cakephp", "yii",
    "rails", "ruby on rails", "sinatra",
    "asp.net", "dotnet", ".net", ".net core", "aspnetcore", "blazor",
    "gin", "echo", "fiber", "beego", "buffalo",
    "phoenix", "play framework", "ktor", "micronaut", "quarkus",
    "actix", "rocket", "axum",
    # Databases
    "postgresql", "postgres", "mysql", "mariadb", "sqlite", "oracle",
    "mongodb", "mongo", "redis", "elasticsearch", "elk", "solr",
    "cassandra", "scylladb", "cockroachdb", "cockroach", "yugabyte",
    "dynamodb", "dynamo", "cosmosdb", "cosmos", "firebase", "firestore",
    "neo4j", "arangodb", "orientdb", "janusgraph",
    "influxdb", "timescaledb", "prometheus", "graphite", "rrd",
    "clickhouse", "vertica", "teradata",
    "bigquery", "big query", "snowflake", "redshift", "athena", "databricks",
    "supabase", "prisma", "sequelize", "typeorm", "hibernate", "jpa",
    "sql", "tsql", "pl/sql", "nosql", "newsql", "graphql",
    # Cloud / DevOps / Infrastructure
    "aws", "amazon web services", "ec2", "s3", "rds", "lambda", "ecs", "eks",
    "azure", "microsoft azure", "azure devops", "azure functions",
    "gcp", "google cloud", "google cloud platform", "app engine", "cloud run",
    "docker", "docker compose", "dockerfile", "kubernetes", "k8s", "helm",
    "terraform", "pulumi", "cloudformation", "ansible", "puppet", "chef",
    "jenkins", "gitlab ci", "gitlab-ci", "github actions", "github-actions",
    "circleci", "travis", "travisci", "bamboo", "teamcity", "argocd", "argo",
    "nginx", "apache", "httpd", "iis", "tomcat", "jetty", "undertow",
    "linux", "ubuntu", "centos", "rhel", "debian", "alpine", "arch",
    "unix", "bash", "zsh", "fish", "powershell",
    "prometheus", "grafana", "datadog", "newrelic", "splunk", "elk",
    "istio", "linkerd", "consul", "vault", "envoy",
    "kafka", "rabbitmq", "sqs", "sns", "eventbridge", "kinesis",
    "redis", "memcached", "varnish", "haproxy",
    "ci/cd", "cicd", "devops", "sre", "platform engineering",
    "microservices", "monolith", "serverless", "faas", "soa", "event-driven",
    # Data / ML / AI
    "tensorflow", "pytorch", "torch", "keras", "jax", "flax", "trax",
    "scikit-learn", "sklearn", "scikitlearn",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly", "bokeh",
    "dask", "ray", "modin", "vaex", "polars", "xarray",
    "spark", "pyspark", "hadoop", "hdfs", "yarn", "mapreduce",
    "airflow", "prefect", "dagster", "luigi", "pinball",
    "kafka", "confluent", "pulsar", "nats", "zeromq",
    "dbt", "dbt core", "dbt cloud", "fivetran", "stitch", "airbyte",
    "mlflow", "kubeflow", "bentoml", "seldon", "ray serve",
    "huggingface", "hugging face", "transformers", "bert", "gpt", "llm",
    "openai", "anthropic", "claude", "langchain", "llamaindex", "chromadb",
    "xgboost", "lightgbm", "catboost", "optuna", "hyperopt",
    "nltk", "spacy", "gensim", "textblob", "corenlp",
    "opencv", "pillow", "scikit-image", "imgaug", "albumentations",
    "nlp", "natural language processing", "computer vision", "cv", "ocr",
    "machine learning", "deep learning", "reinforcement learning", "rl",
    "data science", "data engineering", "data analytics", "bi", "business intelligence",
    "etl", "elt", "data warehouse", "data warehousing", "data lake",
    "tableau", "powerbi", "power bi", "looker", "metabase", "superset",
    "great expectations", "soda", "monte carlo",
    # Mobile
    "react native", "reactnative", "flutter", "dart",
    "ios", "android", "swift", "swiftui", "objective-c", "objc",
    "kotlin", "java android", "jetpack compose", "xml layouts",
    "xamarin", "ionic", "cordova", "phonegap", "capacitor",
    "expo", "detox", "appium", "xctest", "espresso", "robolectric",
    # Security
    "cybersecurity", "infosec", "security", "penetration testing", "pentesting",
    "owasp", "encryption", "cryptography", "tls", "ssl", "pki",
    "oauth", "oidc", "openid connect", "saml", "ldap", "ad",
    "firewall", "waf", "ids", "ips", "siem", "soar",
    "vulnerability scanning", "nessus", "qualys", "burp", "metasploit",
    "devsecops", "shift left", "security scanning", "sast", "dast", "sca",
    # Testing / QA
    "testing", "qa", "quality assurance", "manual testing", "automation testing",
    "selenium", "cypress", "playwright", "puppeteer", "webdriver",
    "jest", "mocha", "chai", "jasmine", "vitest", "ava",
    "pytest", "unittest", "nose", "robot framework",
    "cucumber", "gherkin", "bdd", "tdd", "atdd",
    "junit", "testng", "mockito", "jmock", "easymock",
    "postman", "insomnia", "rest assured", "karate",
    "jmeter", "gatling", "k6", "locust", "artillery",
    "appium", "detox", "maestro", "espresso", "xctest",
    # Tools & Collaboration
    "git", "github", "gitlab", "bitbucket", "svn", "mercurial",
    "jira", "confluence", "trello", "asana", "monday", "linear",
    "slack", "teams", "discord", "zoom",
    "figma", "sketch", "adobe xd", "invision", "zeplin",
    "swagger", "openapi", "postman", "insomnia", "hoppscotch",
    "notion", "obsidian", "roam",
    # Architecture & Methodologies
    "agile", "scrum", "kanban", "lean", "xp", "extreme programming",
    "waterfall", "v-model", "spiral",
    "tdd", "test driven development", "bdd", "behavior driven development",
    "ddd", "domain driven design", "clean architecture", "hexagonal",
    "microservices", "service mesh", "event sourcing", "cqrs",
    "saga pattern", "circuit breaker", "bulkhead", "rate limiting",
    "api gateway", "bff", "backend for frontend",
    "oauth2", "jwt", "api design", "restful", "graphql", "grpc", "protobuf",
    # Soft skills / Domain
    "backend", "backend development", "frontend", "frontend development",
    "fullstack", "full stack", "full-stack", "web development",
    "mobile", "desktop", "embedded", "firmware", "iot", "edge computing",
    "blockchain", "web3", "smart contracts", "defi", "nft",
    "fintech", "healthtech", "edtech", "martech", "ecommerce", "e-commerce",
    "saas", "paas", "iaas", "on-premise", "hybrid cloud", "multi-cloud",
    "english", "tiếng anh", "japanese", "tiếng nhật", "chinese", "tiếng trung",
    "leadership", "team management", "project management", "product management",
    "mentoring", "coaching", "communication", "problem solving",
    # Design / Creative Tools
    "figma", "sketch", "adobe xd", "adobe photoshop", "adobe illustrator",
    "photoshop", "illustrator", "lightroom", "premiere", "after effects",
    "canva", "capcut", "剪映",
    "blender", "cinema 4d", "maya", "3ds max", "zbrush",
    "autocad", "solidworks", "sketchup", "rhino",
    # Marketing / Content
    "content marketing", "content creation", "digital marketing",
    "seo", "sem", "google ads", "facebook ads", "social media marketing",
    "email marketing", "affiliate marketing", "influencer marketing",
    "copywriting", "content strategy", "brand strategy", "market research",
    "google analytics", "google tag manager", "facebook pixel",
    "hubspot", "mailchimp", "wordpress", "shopify", "woocommerce",
    "crm", "salesforce", "zoho", "sap",
})

# Pre-compiled patterns
_YOE_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*\+?\s*(?:year|yr|năm)s?\s*(?:of\s+)?(?:experience|exp|kinh\s*nghiệm)?",
    re.IGNORECASE,
)
_YOE_PATTERN_VI = re.compile(
    r"(?:kinh\s*nghiệm\s*)?(\d+(?:\.\d+)?)\s*\+?\s*năm",
    re.IGNORECASE,
)

# Vietnamese stop words that should NOT be treated as skills
_VI_STOP_WORDS: frozenset[str] = frozenset({
    # Pronouns / common words
    "anh", "chị", "em", "cô", "cậu", "mình", "bạn", "tôi", "tui",
    "có", "không", "và", "hoặc", "nhưng", "vì", "nên", "để", "ở", "tại",
    "công", "cụ", "cơ", "bản", "cắt", "dựng", "lên", "cho", "các", "của",
    "trong", "ngoài", "trên", "dưới", "giữa", "với", "bởi", "từ", "đến",
    "việc", "làm", "là", "thì", "mà", "được", "bị", "đang", "sẽ", "đã",
    "rất", "khá", "cũng", "đều", "chỉ", "còn", "nữa", "mới", "cũ",
    "kỹ", "năng", "thuật", "chuyên", "môn", "tốt", "giỏi", "trung", "bình",
    # Media / creative Vietnamese verbs (often in CV action bullets)
    "quay", "chụp", "dựng", "thiết", "kế", "viết", "soạn", "biên", "tập",
    "quản", "trị", "điều", "hành", "phát", "triển", "thực", "hiện",
    # Business Vietnamese (not tech skills)
    "kinh", "doanh", "bán", "hàng", "khách", "hàng", "thị", "trường",
    "bảo", "hiểm", "ngân", "hàng", "tài", "chính", "kế", "toán",
    # Short ambiguous abbreviations from Vietnamese context
    "cn", "tp", "hcm", "hn", "vn", "gpa", "cv",
    # Common Vietnamese syllables without diacritics (romanized names/words)
    "thuy", "tuan", "hung", "minh", "loan", "hoa", "thanh", "linh", "lan",
    "son", "duc", "hai", "khoa", "long", "phong", "tien", "vinh", "nam",
    "tuyen", "binh", "cuong", "dung", "giang", "huong", "khanh", "nhung",
    "phuong", "quyen", "thao", "thu", "trang", "trung", "van", "yen",
})
# Matches tech tokens: starts with letter, body is alphanum/+/#,
# special separator (./-)  must be followed by more alphanum — prevents
# trailing punctuation like "postgresql." from being captured as "postgresql."
_TOKEN_PATTERN = re.compile(
    r"[a-z][a-z0-9+#]*(?:[./\-][a-z0-9+#]+)*",
    re.IGNORECASE,
)
# Vietnamese skill patterns (for common Vietnamese CV formats)
_VI_SKILL_PATTERNS = [
    re.compile(r'tiếng\s+(anh|nhật|trung|hàn|pháp|đức)', re.I),
    re.compile(r'kỹ\s*năng\s*([a-z]+)', re.I),
    re.compile(r'chuyên\s*môn\s*([a-z]+)', re.I),
    re.compile(r'thành\s*thạo\s*([a-z]+)', re.I),
    re.compile(r'sử\s*dụng\s*tốt\s*([a-z]+)', re.I),
]


# ── Public API ────────────────────────────────────────────────────────────────

def extract_skills(text: str) -> set[str]:
    """
    Extract technical skills from free text.

    Strategy:
    1. Tokenise into lowercase words / short n-grams (1-3 tokens).
    2. Match against the curated _TECH_SKILLS vocabulary.
    3. Extract Vietnamese skill patterns.
    4. Filter out false positives and Vietnamese stop words.

    Returns a set of matched skill strings (lower-cased).
    """
    if not text:
        return set()

    lower = text.lower()
    found: set[str] = set()

    # Single-word matches (with filtering)
    tokens = set(_TOKEN_PATTERN.findall(lower))
    # Filter: remove single letters and Vietnamese stop words
    valid_tokens = {t for t in tokens if t in _TECH_SKILLS and len(t) > 1 and t not in _VI_STOP_WORDS}
    found.update(valid_tokens)

    # Multi-word matches (bigrams and trigrams)
    words = [w for w in lower.split() if len(w) > 1 and w not in _VI_STOP_WORDS]

    # Two-word bigram matches (e.g. "machine learning", "computer vision")
    for i in range(len(words) - 1):
        bigram = f"{words[i]} {words[i+1]}"
        if bigram in _TECH_SKILLS:
            found.add(bigram)

    # Three-word trigram matches (e.g. "natural language processing", "amazon web services")
    for i in range(len(words) - 2):
        trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
        if trigram in _TECH_SKILLS:
            found.add(trigram)

    # Handle dot variants (e.g., "next.js" vs "nextjs", "node.js" vs "nodejs")
    dot_variants = {
        "next.js": "nextjs", "nuxt.js": "nuxtjs", "node.js": "nodejs",
        "express.js": "express", "vue.js": "vue", "react.js": "react",
        "ember.js": "ember", "backbone.js": "backbone",
    }
    for variant, standard in dot_variants.items():
        if variant in lower and standard in _TECH_SKILLS:
            found.add(standard)

    # Vietnamese skill pattern extraction - with better validation
    for pattern in _VI_SKILL_PATTERNS:
        for match in pattern.finditer(text):
            skill = match.group(1).lower().strip()
            # Filter out stop words and single letters
            if skill in _VI_STOP_WORDS or len(skill) < 2:
                continue
            # Must be a known tech skill or at least 3 chars and look like a tech term
            if skill in _TECH_SKILLS:
                found.add(skill)
            elif len(skill) >= 3 and not _looks_like_vietnamese_word(skill):
                found.add(skill)

    return found


def _looks_like_vietnamese_word(word: str) -> bool:
    """Heuristic to detect if a word is likely a common Vietnamese word, not a tech skill."""
    # Common Vietnamese word patterns
    vietnamese_only_chars = set('àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ')
    if any(c in vietnamese_only_chars for c in word.lower()):
        return True
    # Common Vietnamese non-tech words
    common_vi_words = {'kinh', 'doanh', 'bảo', 'hiểm', 'truyền', 'thông', 'viên', 'thành', 'việc', 'làm'}
    if word.lower() in common_vi_words:
        return True
    return False


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
      "3 năm kinh nghiệm", "5 năm"

    Returns 0.0 if nothing is found.
    """
    if not text:
        return 0.0

    values = []

    # English patterns
    matches = _YOE_PATTERN.findall(text)
    for m in matches:
        try:
            if isinstance(m, tuple):
                for g in m:
                    if g:
                        values.append(float(g))
                        break
            else:
                values.append(float(m))
        except (ValueError, TypeError):
            pass

    # Vietnamese patterns
    vi_matches = _YOE_PATTERN_VI.findall(text)
    for m in vi_matches:
        try:
            if isinstance(m, tuple):
                for g in m:
                    if g:
                        values.append(float(g))
                        break
            else:
                values.append(float(m))
        except (ValueError, TypeError):
            pass

    return max(values) if values else 0.0


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
