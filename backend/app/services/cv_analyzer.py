"""
services/cv_analyzer.py
========================
Structured CV analysis: extract skills, education, experience level,
and generate improvement suggestions by comparing against job requirements.

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


@dataclass
class CVProfile:
    """Structured representation of a parsed CV."""
    skills: set[str] = field(default_factory=set)
    education_level: str | None = None
    years_of_experience: float = 0.0
    job_level_hint: str | None = None
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
                values.append(float(m))
            except (ValueError, TypeError):
                pass
    return max(values) if values else 0.0


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


def extract_skills_from_cv(cv_text: str, jd_skill_pool: set[str] | None = None) -> set[str]:
    """
    Extract skills from CV text.

    Strategy:
    1. Match against the curated tech-skill vocabulary (from feature_engine)
    2. Also match against all skills found in JD pool (covers domain-specific terms)
    """
    from app.ml.feature_engine import extract_skills as base_extract

    found = base_extract(cv_text)

    # Also match against JD skill pool (case-insensitive)
    if jd_skill_pool:
        lower_text = cv_text.lower()
        for skill in jd_skill_pool:
            skill_lower = skill.lower().strip()
            if len(skill_lower) >= 2 and skill_lower in lower_text:
                found.add(skill_lower)

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
        all_jd_skills.update(s.lower().strip() for s in jd_skills if s)
    if jd_requirement:
        all_jd_skills.update(base_extract(jd_requirement))
    if jd_description:
        all_jd_skills.update(base_extract(jd_description))

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

    return tips, top_missing


def analyze_cv(
    cv_text: str,
    jd_skill_pool: set[str] | None = None,
) -> CVProfile:
    """Parse CV text into a structured profile."""
    profile = CVProfile(raw_text=cv_text)
    profile.skills = extract_skills_from_cv(cv_text, jd_skill_pool)
    profile.education_level = extract_education(cv_text)
    profile.years_of_experience = extract_yoe(cv_text)
    profile.job_level_hint = detect_job_level(cv_text)
    return profile
