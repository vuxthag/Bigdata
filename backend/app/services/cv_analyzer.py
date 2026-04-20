"""
services/cv_analyzer.py
========================
Structured CV analysis: extract skills, education, experience level,
CV sections, career direction, and generate improvement suggestions.

Supports both English and Vietnamese text patterns.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ── Education levels (ordered low → high) ────────────────────────────────────

EDUCATION_LEVELS = [
    "high_school",
    "associate",
    "bachelor",
    "master",
    "phd",
]

_EDUCATION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("phd", re.compile(
        r"(?:ph\.?d|doctor(?:ate)?|tiến\s*s[ĩi])", re.IGNORECASE
    )),
    ("master", re.compile(
        r"(?:master(?:'?s)?|m\.?sc?\.?|thạc\s*s[ĩi]|cao\s*học)", re.IGNORECASE
    )),
    ("bachelor", re.compile(
        r"(?:bachelor(?:'?s)?|b\.?sc?\.?|b\.?eng|cử\s*nhân|đại\s*học|university|kỹ\s*sư)", re.IGNORECASE
    )),
    ("associate", re.compile(
        r"(?:associate|cao\s*đẳng|diploma)", re.IGNORECASE
    )),
    ("high_school", re.compile(
        r"(?:high\s*school|trung\s*học|thpt|phổ\s*thông)", re.IGNORECASE
    )),
]

# ── Job level mapping ────────────────────────────────────────────────────────

JOB_LEVEL_ORDER = {
    "intern": 0, "thực tập": 0, "internship": 0,
    "fresher": 1, "entry": 1, "junior": 1, "mới ra trường": 1,
    "nhân viên": 2, "staff": 2, "associate": 2,
    "mid": 3, "middle": 3, "intermediate": 3,
    "senior": 4, "chuyên viên": 4, "experienced": 4,
    "lead": 5, "team lead": 5, "trưởng nhóm": 5,
    "manager": 6, "quản lý": 6, "trưởng phòng": 6,
    "director": 7, "giám đốc": 7, "phó giám đốc": 7,
    "vp": 8, "vice president": 8,
    "c-level": 9, "cto": 9, "ceo": 9, "cfo": 9, "coo": 9,
}

# ── YOE patterns (English + Vietnamese) ─────────────────────────────────────

_YOE_PATTERNS = [
    re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:year|yr)s?\s*(?:of\s+)?(?:experience|exp)", re.I),
    re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*năm\s*(?:kinh\s*nghiệm)?", re.I),
    re.compile(r"(?:experience|kinh\s*nghiệm)\s*:?\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:year|yr|năm)", re.I),
]

# ── Section header patterns ──────────────────────────────────────────────────

_SECTION_HEADERS = {
    "summary": re.compile(
        r"(?:^|\n)\s*(?:tóm\s*tắt|mục\s*tiêu|objective|summary|profile|giới\s*thiệu|career\s*(?:objective|goal)s?|about\s*me)",
        re.I,
    ),
    "education": re.compile(
        r"(?:^|\n)\s*(?:học\s*vấn|education|trình\s*độ\s*học\s*vấn|quá\s*trình\s*(?:đào\s*tạo|học\s*tập)|academic)",
        re.I,
    ),
    "experience": re.compile(
        r"(?:^|\n)\s*(?:kinh\s*nghiệm|experience|work\s*(?:experience|history)|quá\s*trình\s*(?:làm\s*việc|công\s*tác)|projects?|dự\s*án)",
        re.I,
    ),
    "skills": re.compile(
        r"(?:^|\n)\s*(?:kỹ\s*năng|skills?|technical\s*skills?|năng\s*lực|chuyên\s*môn|competenc)",
        re.I,
    ),
    "certifications": re.compile(
        r"(?:^|\n)\s*(?:chứng\s*chỉ|certification|certificate|bằng\s*cấp|licenses?|giấy\s*phép)",
        re.I,
    ),
    "languages": re.compile(
        r"(?:^|\n)\s*(?:ngôn\s*ngữ|language|ngoại\s*ngữ|foreign\s*language)",
        re.I,
    ),
    "interests": re.compile(
        r"(?:^|\n)\s*(?:sở\s*thích|interest|hobbies|hobby|hoạt\s*động)",
        re.I,
    ),
    "references": re.compile(
        r"(?:^|\n)\s*(?:người\s*tham\s*chiếu|reference|referees?)",
        re.I,
    ),
}

# ── Personal info patterns ───────────────────────────────────────────────────

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_PATTERN = re.compile(r"(?:\+84|0)\s*\d[\d\s\-().]{7,}\d")
_LINKEDIN_PATTERN = re.compile(r"linkedin\.com/in/[a-zA-Z0-9_-]+", re.I)
_GITHUB_PATTERN = re.compile(r"github\.com/[a-zA-Z0-9_-]+", re.I)

# ── Work experience patterns ─────────────────────────────────────────────────

_DATE_RANGE_PATTERN = re.compile(
    r"(?:(\d{1,2})[/\-.])?(\d{4})\s*[-–—~]\s*(?:(?:(\d{1,2})[/\-.])?(\d{4})|(?:hiện\s*tại|nay|present|current|now|đến\s*nay))",
    re.I,
)

# More flexible date pattern for various formats
_DATE_RANGE_PATTERN_VI = re.compile(
    r"(?:từ\s+)?(?:(\d{1,2})[/\-.])?(\d{4})(?:\s*[-–—~]\s*|\s*đến\s*)(?:(?:(\d{1,2})[/\-.])?(\d{4})|(?:hiện\s*tại|nay|đến\s*nay))",
    re.I,
)
_COMPANY_ROLE_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:at|tại|@)?\s*(.+?)(?:\s*[-–|]\s*(.+))?\s*(?:\d{4})",
    re.I,
)

# ── Skill categories ─────────────────────────────────────────────────────────

_SKILL_CATEGORIES = {
    "Ngôn ngữ lập trình": {
        "python", "javascript", "typescript", "java", "kotlin", "swift", "c", "c++",
        "c#", "go", "golang", "rust", "ruby", "php", "scala", "r", "matlab",
        "bash", "shell", "powershell", "dart",
    },
    "Frontend": {
        "react", "vue", "angular", "svelte", "nextjs", "nuxtjs", "redux", "html",
        "css", "sass", "tailwindcss", "bootstrap", "webpack", "vite", "graphql",
    },
    "Backend": {
        "django", "flask", "fastapi", "spring", "springboot", "express", "nodejs",
        "nestjs", "laravel", "rails", "asp.net", "dotnet", "rest", "restful",
    },
    "Database": {
        "postgresql", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
        "cassandra", "dynamodb", "oracle", "mssql", "neo4j", "sql", "nosql",
        "bigquery", "snowflake",
    },
    "Cloud / DevOps": {
        "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform",
        "ansible", "jenkins", "github actions", "gitlab ci", "nginx", "linux",
        "ci/cd", "devops",
    },
    "Data / AI / ML": {
        "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "pandas",
        "numpy", "scipy", "spark", "hadoop", "airflow", "kafka", "dbt", "mlflow",
        "huggingface", "transformers", "bert", "llm", "openai", "xgboost",
        "lightgbm", "nlp", "computer vision", "machine learning", "deep learning",
        "data science", "data engineering",
    },
    "Tools": {
        "git", "github", "gitlab", "bitbucket", "jira", "confluence", "figma",
        "postman", "swagger", "openapi",
    },
    "Methodology": {
        "agile", "scrum", "kanban", "tdd", "bdd", "microservices", "serverless",
    },
}

# ── Career direction mapping ─────────────────────────────────────────────────

_CAREER_DIRECTIONS = [
    {
        "title": "Backend Developer",
        "keywords": {"python", "java", "fastapi", "django", "flask", "spring", "nodejs",
                     "express", "nestjs", "rest", "restful", "sql", "postgresql", "mysql",
                     "mongodb", "redis", "docker", "api"},
        "description": "Phát triển hệ thống backend, API, microservices",
    },
    {
        "title": "Frontend Developer",
        "keywords": {"react", "vue", "angular", "svelte", "javascript", "typescript",
                     "html", "css", "nextjs", "redux", "tailwindcss", "webpack", "vite"},
        "description": "Phát triển giao diện web, SPA, UI/UX",
    },
    {
        "title": "Full-stack Developer",
        "keywords": {"react", "vue", "angular", "nodejs", "python", "java", "sql",
                     "mongodb", "docker", "fullstack", "full stack", "full-stack"},
        "description": "Phát triển toàn bộ ứng dụng web (frontend + backend)",
    },
    {
        "title": "Data Engineer",
        "keywords": {"python", "sql", "spark", "hadoop", "airflow", "kafka", "etl",
                     "data engineering", "bigquery", "snowflake", "dbt", "postgresql"},
        "description": "Xây dựng pipeline dữ liệu, ETL, data warehouse",
    },
    {
        "title": "Data Scientist / ML Engineer",
        "keywords": {"python", "machine learning", "deep learning", "tensorflow",
                     "pytorch", "scikit-learn", "pandas", "numpy", "nlp",
                     "computer vision", "data science", "xgboost", "bert", "llm"},
        "description": "Phân tích dữ liệu, xây dựng mô hình AI/ML",
    },
    {
        "title": "DevOps / Cloud Engineer",
        "keywords": {"docker", "kubernetes", "aws", "azure", "gcp", "terraform",
                     "ansible", "jenkins", "ci/cd", "devops", "linux", "nginx",
                     "github actions", "gitlab ci"},
        "description": "Quản lý hạ tầng cloud, CI/CD, automation",
    },
    {
        "title": "Mobile Developer",
        "keywords": {"swift", "kotlin", "react native", "flutter", "dart",
                     "ios", "android", "mobile"},
        "description": "Phát triển ứng dụng di động iOS/Android",
    },
    {
        "title": "QA / Test Engineer",
        "keywords": {"testing", "selenium", "cypress", "jest", "pytest", "qa",
                     "quality assurance", "automation testing", "tdd", "bdd"},
        "description": "Kiểm thử phần mềm, tự động hóa testing",
    },
    {
        "title": "Security Engineer",
        "keywords": {"security", "cybersecurity", "devsecops", "penetration",
                     "owasp", "encryption", "firewall"},
        "description": "Bảo mật hệ thống, kiểm tra lỗ hổng",
    },
    {
        "title": "Project Manager / Scrum Master",
        "keywords": {"agile", "scrum", "kanban", "jira", "confluence", "management",
                     "quản lý", "trưởng nhóm", "team lead", "manager"},
        "description": "Quản lý dự án, điều phối đội ngũ phát triển",
    },
]


@dataclass
class CVSection:
    """A detected section of the CV."""
    name: str
    content: str


@dataclass
class WorkExperience:
    """A detected work experience entry."""
    title: str = ""
    company: str = ""
    period: str = ""
    description: str = ""


@dataclass
class EducationEntry:
    """A detected education entry."""
    degree: str = ""
    school: str = ""
    period: str = ""
    details: str = ""


@dataclass
class CareerDirection:
    """A suggested career direction."""
    title: str = ""
    match_score: float = 0.0
    description: str = ""
    matched_skills: list[str] = field(default_factory=list)
    suggested_skills: list[str] = field(default_factory=list)


@dataclass
class CVProfile:
    """Structured representation of a parsed CV."""
    skills: set[str] = field(default_factory=set)
    skills_by_category: dict[str, list[str]] = field(default_factory=dict)
    education_level: str | None = None
    education_entries: list[EducationEntry] = field(default_factory=list)
    years_of_experience: float = 0.0
    work_experiences: list[WorkExperience] = field(default_factory=list)
    job_level_hint: str | None = None
    summary: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    linkedin: str = ""
    github: str = ""
    certifications: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    sections_found: list[str] = field(default_factory=list)
    career_directions: list[CareerDirection] = field(default_factory=list)
    raw_text: str = ""


@dataclass
class JobMatch:
    """Per-job matching breakdown."""
    job_id: str
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    education_match: bool = True
    level_match: bool = True
    yoe_match: bool = True


@dataclass
class CVAnalysisResult:
    """Full CV analysis output."""
    cv_skills: list[str] = field(default_factory=list)
    education_level: str | None = None
    years_of_experience: float = 0.0
    detected_level: str | None = None
    job_matches: list[JobMatch] = field(default_factory=list)
    improvement_tips: list[str] = field(default_factory=list)
    top_missing_skills: list[str] = field(default_factory=list)


# ── Extraction functions ─────────────────────────────────────────────────────

def extract_education(text: str) -> str | None:
    """Detect the highest education level mentioned in text."""
    if not text:
        return None
    for level, pattern in _EDUCATION_PATTERNS:
        if pattern.search(text):
            return level
    return None


def extract_yoe(text: str) -> float:
    """Extract years of experience from text (EN + VI patterns)."""
    if not text:
        return 0.0
    values: list[float] = []
    for pat in _YOE_PATTERNS:
        for m in pat.findall(text):
            try:
                # Handle both string and tuple returns from regex
                if isinstance(m, tuple):
                    # Take first non-empty group
                    for group in m:
                        if group:
                            values.append(float(group))
                            break
                else:
                    values.append(float(m))
            except (ValueError, TypeError):
                pass
    # Also try to calculate from date ranges in experience section
    date_yoe = _calculate_yoe_from_dates(text)
    if date_yoe > 0:
        values.append(date_yoe)
    return max(values) if values else 0.0


def _calculate_yoe_from_dates(text: str) -> float:
    """Calculate total YOE by summing date ranges found in text."""
    import datetime
    total_months = 0
    seen_ranges = set()  # Track unique ranges to avoid double counting

    for match in _DATE_RANGE_PATTERN.finditer(text):
        start_year = int(match.group(2))
        start_month = int(match.group(1)) if match.group(1) else 1
        end_year_str = match.group(4)
        end_month_str = match.group(3)

        # Create a key for deduplication
        range_key = (start_year, start_month, end_year_str, end_month_str)
        if range_key in seen_ranges:
            continue
        seen_ranges.add(range_key)

        if end_year_str:
            end_year = int(end_year_str)
            end_month = int(end_month_str) if end_month_str else 12
        else:
            # "Present" or "current" - use current date
            now = datetime.datetime.now()
            end_year = now.year
            end_month = now.month

        # Calculate months
        months = (end_year - start_year) * 12 + (end_month - start_month)
        if months > 0:
            total_months += months

    return round(total_months / 12, 1)


def detect_job_level(text: str) -> str | None:
    """Detect the job level/seniority from CV text."""
    if not text:
        return None
    lower = text.lower()
    best_level: str | None = None
    best_order = -1
    for keyword, order in JOB_LEVEL_ORDER.items():
        if keyword in lower and order > best_order:
            best_level = keyword
            best_order = order
    return best_level


def extract_contact_info(text: str) -> tuple[str, str, str, str]:
    """Extract email, phone, LinkedIn, GitHub from text."""
    email_m = _EMAIL_PATTERN.search(text)
    phone_m = _PHONE_PATTERN.search(text)
    linkedin_m = _LINKEDIN_PATTERN.search(text)
    github_m = _GITHUB_PATTERN.search(text)
    return (
        email_m.group() if email_m else "",
        phone_m.group() if phone_m else "",
        linkedin_m.group() if linkedin_m else "",
        github_m.group() if github_m else "",
    )


def extract_sections(text: str) -> dict[str, str]:
    """
    Split CV text into sections by detecting section headers.
    Returns dict of section_name -> section_content.
    """
    if not text:
        return {}

    # Find all section header positions
    matches: list[tuple[str, int]] = []
    for section_name, pattern in _SECTION_HEADERS.items():
        for m in pattern.finditer(text):
            matches.append((section_name, m.start()))

    if not matches:
        return {"full_text": text}

    # Sort by position
    matches.sort(key=lambda x: x[1])

    sections: dict[str, str] = {}
    for i, (name, start) in enumerate(matches):
        # Find the header end (next line)
        header_end = text.find("\n", start)
        if header_end == -1:
            header_end = start + 50
        content_start = header_end + 1

        # Content ends at next section or end of text
        if i + 1 < len(matches):
            content_end = matches[i + 1][1]
        else:
            content_end = len(text)

        content = text[content_start:content_end].strip()
        if content:
            sections[name] = content

    return sections


def _extract_work_experiences(text: str) -> list[WorkExperience]:
    """Extract work experience entries from experience section text."""
    experiences: list[WorkExperience] = []
    lines = text.strip().split("\n")
    current = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        date_match = _DATE_RANGE_PATTERN.search(line)
        if date_match:
            if current:
                experiences.append(current)
            current = WorkExperience()
            current.period = date_match.group().strip()
            remaining = _DATE_RANGE_PATTERN.sub("", line).strip(" -–—|•:·")
            parts = re.split(r"\s*[-–|]\s*", remaining, maxsplit=1)
            if len(parts) >= 2:
                current.title = parts[0].strip()
                current.company = parts[1].strip()
            elif parts[0]:
                current.title = parts[0].strip()
        elif current:
            if current.description:
                current.description += "\n" + line
            else:
                current.description = line

    if current:
        experiences.append(current)

    return experiences


def _extract_education_entries(text: str) -> list[EducationEntry]:
    """Extract education entries from education section text."""
    entries: list[EducationEntry] = []
    lines = text.strip().split("\n")
    current = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        date_match = _DATE_RANGE_PATTERN.search(line)
        has_edu_keyword = bool(re.search(
            r"(?:đại\s*học|university|college|trường|học\s*viện|bachelor|master|thạc|tiến|cử\s*nhân|cao\s*đẳng)",
            line, re.I,
        ))

        if date_match or has_edu_keyword:
            if current:
                entries.append(current)
            current = EducationEntry()
            if date_match:
                current.period = date_match.group().strip()
            remaining = _DATE_RANGE_PATTERN.sub("", line).strip(" -–—|•:·")
            parts = re.split(r"\s*[-–|]\s*", remaining, maxsplit=1)
            if len(parts) >= 2:
                current.school = parts[0].strip()
                current.degree = parts[1].strip()
            elif parts[0]:
                current.school = parts[0].strip()
        elif current:
            if current.details:
                current.details += "\n" + line
            else:
                current.details = line

    if current:
        entries.append(current)

    return entries


def _extract_list_items(text: str) -> list[str]:
    """Extract list items from a section (certs, languages, etc.)."""
    items: list[str] = []
    for line in text.split("\n"):
        line = re.sub(r"^[\s•\-*·▸→]+", "", line).strip()
        if line and len(line) > 1:
            items.append(line)
    return items


def categorize_skills(skills: set[str]) -> dict[str, list[str]]:
    """Categorize skills into groups."""
    categorized: dict[str, list[str]] = {}
    uncategorized: list[str] = []

    for skill in sorted(skills):
        found = False
        for category, category_skills in _SKILL_CATEGORIES.items():
            if skill.lower() in category_skills:
                categorized.setdefault(category, []).append(skill)
                found = True
                break
        if not found:
            uncategorized.append(skill)

    if uncategorized:
        categorized["Khác"] = uncategorized

    return categorized


def suggest_career_directions(skills: set[str]) -> list[CareerDirection]:
    """Suggest career directions based on CV skills."""
    directions: list[CareerDirection] = []
    skills_lower = {s.lower() for s in skills}

    for cd in _CAREER_DIRECTIONS:
        matched = skills_lower & cd["keywords"]
        if not matched:
            continue
        score = len(matched) / len(cd["keywords"])
        suggested = sorted(cd["keywords"] - skills_lower)[:5]

        directions.append(CareerDirection(
            title=cd["title"],
            match_score=round(score, 2),
            description=cd["description"],
            matched_skills=sorted(matched),
            suggested_skills=suggested,
        ))

    directions.sort(key=lambda d: d.match_score, reverse=True)
    return directions[:4]


def extract_skills_from_cv(cv_text: str, jd_skill_pool: set[str] | None = None) -> set[str]:
    """
    Extract skills from CV text using multi-strategy approach.

    Strategy:
    1. Match against the curated tech-skill vocabulary (from feature_engine)
    2. Match against all skills found in JD pool (covers domain-specific terms)
    3. Extract from dedicated skills section with bullet points
    4. Extract multi-word skills using n-gram matching
    5. Filter out Vietnamese stop words and false positives
    """
    from app.ml.feature_engine import extract_skills as base_extract, _VI_STOP_WORDS, _looks_like_vietnamese_word

    found = base_extract(cv_text)

    # Strategy 2: Match against JD skill pool (case-insensitive, word boundary aware)
    if jd_skill_pool:
        lower_text = cv_text.lower()
        for skill in jd_skill_pool:
            skill_lower = skill.lower().strip()
            if len(skill_lower) < 2 or skill_lower in _VI_STOP_WORDS:
                continue
            # Use word boundary matching for precision
            if len(skill_lower.split()) > 1:
                # Multi-word skill: check if it exists as substring
                if skill_lower in lower_text:
                    found.add(skill_lower)
            else:
                # Single-word skill: use word boundary check
                import re
                pattern = r'\b' + re.escape(skill_lower) + r'\b'
                if re.search(pattern, lower_text, re.IGNORECASE):
                    found.add(skill_lower)

    # Strategy 3: Extract from skills section specifically
    sections = extract_sections(cv_text)
    if "skills" in sections:
        skills_text = sections["skills"]
        # Parse bullet points, commas, and newlines
        skill_items = re.split(r'[,;•\-*·▸→\n]', skills_text)
        for item in skill_items:
            item = item.strip().lower()
            if 2 <= len(item) <= 50 and not item.isdigit():
                # Clean up common prefixes/suffixes
                item = re.sub(r'^(?:kỹ\s*năng|skills?|năng\s*lực|chuyên\s*môn)[:\s]*', '', item, flags=re.I)
                item = re.sub(r'\s*\([^)]*\)$', '', item)  # Remove trailing (level)
                item = item.strip()
                # Filter out Vietnamese stop words and common non-tech terms
                if item and item not in _VI_STOP_WORDS and not _looks_like_vietnamese_word(item):
                    found.add(item)

    # Strategy 4: Extract from experience section - look for technology mentions
    if "experience" in sections:
        exp_text = sections["experience"].lower()
        # Look for "with X", "using X", "in X" patterns
        tool_patterns = [
            r'(?:with|using|in|on)\s+([a-z]+(?:\s+[a-z]+){0,2})',
            r'(?:technologies?|stack|tools?)[:\s]+([a-z0-9+#.,\s]+)',
        ]
        for pattern in tool_patterns:
            for match in re.finditer(pattern, exp_text, re.I):
                tech = match.group(1).strip().lower()
                # Split by common delimiters and validate
                for part in re.split(r'[,;&/]', tech):
                    part = part.strip()
                    if 2 <= len(part) <= 30 and not part.isdigit():
                        if part not in _VI_STOP_WORDS and not _looks_like_vietnamese_word(part):
                            found.add(part)

    # Final filter: remove any remaining Vietnamese stop words
    found = {s for s in found if s not in _VI_STOP_WORDS and not _looks_like_vietnamese_word(s)}

    return found


def build_jd_skill_pool(jd_skills_arrays: list[list[str] | None]) -> set[str]:
    """Build a unified set of all skills from the JD pool."""
    pool: set[str] = set()
    for arr in jd_skills_arrays:
        if arr:
            for s in arr:
                if s and len(s.strip()) >= 2:
                    pool.add(s.strip().lower())
    return pool


# ── Matching logic ───────────────────────────────────────────────────────────

def _education_rank(level: str | None) -> int:
    if not level:
        return -1
    try:
        return EDUCATION_LEVELS.index(level)
    except ValueError:
        return -1


def _level_rank(level_str: str | None) -> int:
    if not level_str:
        return -1
    return JOB_LEVEL_ORDER.get(level_str.lower().strip(), -1)


def _is_valid_skill(skill: str) -> bool:
    """Check if a skill string is valid (not a Vietnamese word, not too short)."""
    from app.ml.feature_engine import _VI_STOP_WORDS, _looks_like_vietnamese_word
    s = skill.strip().lower()
    if not s or len(s) < 2:
        return False
    # Single-letter skills are invalid
    if len(s) == 1:
        return False
    # Filter out 2-letter abbreviations unless they're unambiguous known tech ones
    VALID_SHORT = {'go', 'c#', 'c++', 'ai', 'ml', 'qa', 'ui', 'ux', 'it', 'js', 'ts', 'r'}
    if len(s) == 2 and s not in VALID_SHORT:
        return False
    if s in _VI_STOP_WORDS:
        return False
    if _looks_like_vietnamese_word(s):
        return False
    # Filter skills that look like names (single capitalized word, no tech chars)
    # Skills that are purely lowercase ASCII letters and less than 3 chars are suspicious
    if len(s) == 2 and s.isalpha() and s not in VALID_SHORT:
        return False
    # Filter generic Vietnamese sentences/phrases
    if len(s) > 60:
        return False
    # Must contain at least one ASCII letter (filter out pure Vietnamese/numeric noise)
    if not any(c.isascii() and c.isalpha() for c in s):
        return False
    return True


def compute_job_match(
    cv_profile: CVProfile,
    jd_skills: list[str] | None,
    jd_requirement: str | None,
    jd_description: str | None,
    jd_yoe: int | None,
    jd_level: str | None,
    jd_education_text: str | None = None,
) -> JobMatch:
    """
    Compute per-job matching breakdown: matched/missing skills,
    education compatibility, level compatibility, YOE compatibility.
    """
    match = JobMatch(job_id="")

    # Build full JD skill set: stored skills + extracted from requirement + description
    from app.ml.feature_engine import extract_skills as base_extract

    all_jd_skills: set[str] = set()
    if jd_skills:
        # Filter JD stored skills — remove Vietnamese non-tech words
        for s in jd_skills:
            if s and _is_valid_skill(s):
                all_jd_skills.add(s.lower().strip())
    if jd_requirement:
        all_jd_skills.update(s for s in base_extract(jd_requirement) if _is_valid_skill(s))
    if jd_description:
        all_jd_skills.update(s for s in base_extract(jd_description) if _is_valid_skill(s))

    cv_skills_lower = {s.lower() for s in cv_profile.skills}

    match.matched_skills = sorted(cv_skills_lower & all_jd_skills)
    match.missing_skills = sorted(all_jd_skills - cv_skills_lower)

    # Education match
    if jd_education_text:
        jd_edu = extract_education(jd_education_text)
        if jd_edu and cv_profile.education_level:
            match.education_match = _education_rank(cv_profile.education_level) >= _education_rank(jd_edu)
    if jd_requirement:
        jd_edu = extract_education(jd_requirement)
        if jd_edu and cv_profile.education_level:
            match.education_match = _education_rank(cv_profile.education_level) >= _education_rank(jd_edu)

    # YOE match
    effective_jd_yoe = jd_yoe or 0
    if effective_jd_yoe > 0:
        match.yoe_match = cv_profile.years_of_experience >= effective_jd_yoe * 0.7

    # Level match
    if jd_level:
        jd_rank = _level_rank(jd_level)
        cv_rank = _level_rank(cv_profile.job_level_hint)
        if jd_rank >= 0 and cv_rank >= 0:
            match.level_match = cv_rank >= jd_rank - 1

    return match


def generate_improvement_tips(
    cv_profile: CVProfile,
    job_matches: list[JobMatch],
) -> tuple[list[str], list[str]]:
    """
    Generate actionable CV improvement tips based on analysis.
    Returns (tips, top_missing_skills).
    """
    tips: list[str] = []

    # Aggregate missing skills across all recommended jobs
    missing_counter: dict[str, int] = {}
    for jm in job_matches:
        for skill in jm.missing_skills:
            missing_counter[skill] = missing_counter.get(skill, 0) + 1

    # Top missing skills: most frequently required across jobs
    sorted_missing = sorted(missing_counter.items(), key=lambda x: -x[1])
    top_missing = [s for s, _ in sorted_missing[:10]]

    if top_missing:
        top_3 = ", ".join(top_missing[:3])
        tips.append(
            f"Các kỹ năng được yêu cầu nhiều nhất mà CV chưa có: {top_3}. "
            f"Hãy bổ sung các kỹ năng này vào CV nếu bạn có kinh nghiệm liên quan."
        )

    # Education tip
    if not cv_profile.education_level:
        tips.append(
            "CV chưa đề cập rõ trình độ học vấn. Hãy bổ sung thông tin bằng cấp "
            "(Đại học, Thạc sĩ, ...) để AI đánh giá chính xác hơn."
        )

    # YOE tip
    if cv_profile.years_of_experience == 0:
        tips.append(
            "CV chưa nêu rõ số năm kinh nghiệm. Hãy ghi rõ thời gian làm việc "
            "tại mỗi vị trí (ví dụ: '3 năm kinh nghiệm Python') để AI so khớp tốt hơn."
        )

    # Skills count tip
    if len(cv_profile.skills) < 5:
        tips.append(
            f"CV chỉ phát hiện được {len(cv_profile.skills)} kỹ năng kỹ thuật. "
            "Hãy liệt kê rõ ràng các kỹ năng/công nghệ bạn thành thạo trong mục 'Kỹ năng'."
        )

    # Job level tip
    if not cv_profile.job_level_hint:
        tips.append(
            "CV chưa thể hiện rõ cấp bậc (Junior, Senior, Lead...). "
            "Hãy đề cập rõ vai trò và trách nhiệm để AI gợi ý đúng cấp bậc."
        )

    # Non-matching education
    edu_misses = sum(1 for jm in job_matches if not jm.education_match)
    if edu_misses > 0:
        tips.append(
            f"{edu_misses}/{len(job_matches)} công việc yêu cầu trình độ học vấn cao hơn. "
            "Cân nhắc bổ sung chứng chỉ hoặc các khóa học chuyên sâu."
        )

    # Career direction tip
    if cv_profile.career_directions:
        top_dir = cv_profile.career_directions[0]
        if top_dir.suggested_skills:
            s_list = ", ".join(top_dir.suggested_skills[:3])
            tips.append(
                f"Định hướng phù hợp nhất: {top_dir.title}. "
                f"Để tăng cơ hội, hãy học thêm: {s_list}."
            )

    # Section completeness
    expected = {"education", "experience", "skills"}
    found = set(cv_profile.sections_found)
    missing_sections = expected - found
    if missing_sections:
        labels = {"education": "Học vấn", "experience": "Kinh nghiệm", "skills": "Kỹ năng"}
        missing_labels = [labels.get(s, s) for s in missing_sections]
        tips.append(
            f"CV chưa có mục rõ ràng cho: {', '.join(missing_labels)}. "
            "Hãy thêm tiêu đề rõ ràng cho từng phần để AI phân tích tốt hơn."
        )

    return tips, top_missing


def analyze_cv(
    cv_text: str,
    jd_skill_pool: set[str] | None = None,
) -> CVProfile:
    """Parse CV text into a structured profile with detailed sections."""
    profile = CVProfile(raw_text=cv_text)

    # Basic extractions
    profile.skills = extract_skills_from_cv(cv_text, jd_skill_pool)
    profile.education_level = extract_education(cv_text)
    profile.years_of_experience = extract_yoe(cv_text)
    profile.job_level_hint = detect_job_level(cv_text)

    # Contact info
    profile.contact_email, profile.contact_phone, profile.linkedin, profile.github = extract_contact_info(cv_text)

    # Sections
    sections = extract_sections(cv_text)
    profile.sections_found = list(sections.keys())

    # Summary
    if "summary" in sections:
        profile.summary = sections["summary"][:500]
    else:
        # Try first paragraph as summary
        lines = cv_text.strip().split("\n")
        first_lines = []
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 30:
                first_lines.append(line)
            if len(first_lines) >= 3:
                break
        if first_lines:
            profile.summary = " ".join(first_lines)[:500]

    # Education entries
    if "education" in sections:
        profile.education_entries = _extract_education_entries(sections["education"])

    # Work experience
    if "experience" in sections:
        profile.work_experiences = _extract_work_experiences(sections["experience"])

    # Calculate YOE from dates if not found by pattern
    if profile.years_of_experience == 0 and profile.work_experiences:
        exp_text = sections.get("experience", "")
        date_yoe = _calculate_yoe_from_dates(exp_text)
        if date_yoe > 0:
            profile.years_of_experience = date_yoe

    # Certifications
    if "certifications" in sections:
        profile.certifications = _extract_list_items(sections["certifications"])

    # Languages
    if "languages" in sections:
        profile.languages = _extract_list_items(sections["languages"])

    # Categorize skills
    profile.skills_by_category = categorize_skills(profile.skills)

    # Career directions
    profile.career_directions = suggest_career_directions(profile.skills)

    return profile
