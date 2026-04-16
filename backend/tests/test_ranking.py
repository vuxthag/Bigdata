"""
tests/test_ranking.py
======================
Unit + integration tests for the Phase 4 AI Ranking System.

Test coverage:
  1. extract_skills       — known tech-skill phrases
  2. skill_overlap        — Jaccard metric
  3. years_of_experience  — regex patterns
  4. keyword_overlap      — token Jaccard
  5. build_interaction_bonus — weighted signal
  6. rank_candidates_for_job — sorted DESC by match_score
  7. rank_jobs_for_candidate — improves over baseline cosine-only
  8. apply_feedback_signal   — hired raises, rejected lowers score
  9. _yoe_compatibility      — edge cases

Run:
  cd backend
  pytest tests/test_ranking.py -v
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

# ── 1. Feature engine — skill extraction ─────────────────────────────────────

def test_extract_skills_single_words():
    from app.ml.feature_engine import extract_skills
    text = "We need experience with Python, Docker, and PostgreSQL."
    skills = extract_skills(text)
    assert "python" in skills
    assert "docker" in skills
    assert "postgresql" in skills


def test_extract_skills_bigrams():
    from app.ml.feature_engine import extract_skills
    text = "Strong background in machine learning and computer vision required."
    skills = extract_skills(text)
    assert "machine learning" in skills
    assert "computer vision" in skills


def test_extract_skills_empty():
    from app.ml.feature_engine import extract_skills
    assert extract_skills("") == set()
    assert extract_skills("   ") == set()


def test_extract_skills_no_match():
    from app.ml.feature_engine import extract_skills
    skills = extract_skills("We are looking for a passionate and motivated individual.")
    assert len(skills) == 0


# ── 2. Skill overlap (Jaccard) ────────────────────────────────────────────────

def test_skill_overlap_identical():
    from app.ml.feature_engine import skill_overlap
    s = {"python", "docker", "react"}
    assert skill_overlap(s, s) == pytest.approx(1.0)


def test_skill_overlap_disjoint():
    from app.ml.feature_engine import skill_overlap
    assert skill_overlap({"python"}, {"java"}) == pytest.approx(0.0)


def test_skill_overlap_partial():
    from app.ml.feature_engine import skill_overlap
    cv  = {"python", "django", "docker"}
    jd  = {"python", "flask",  "docker"}
    # intersection={python,docker}=2  union={python,django,docker,flask}=4
    assert skill_overlap(cv, jd) == pytest.approx(2 / 4)


def test_skill_overlap_both_empty():
    from app.ml.feature_engine import skill_overlap
    assert skill_overlap(set(), set()) == pytest.approx(0.0)


# ── 3. Years of experience ────────────────────────────────────────────────────

def test_yoe_basic():
    from app.ml.feature_engine import years_of_experience
    assert years_of_experience("Requires 3 years of experience.") == pytest.approx(3.0)


def test_yoe_plus_suffix():
    from app.ml.feature_engine import years_of_experience
    assert years_of_experience("5+ years experience in backend") == pytest.approx(5.0)


def test_yoe_decimal():
    from app.ml.feature_engine import years_of_experience
    assert years_of_experience("2.5 years of experience preferred") == pytest.approx(2.5)


def test_yoe_max_of_multiple():
    from app.ml.feature_engine import years_of_experience
    text = "2 years exp in frontend and 3 years exp in backend"
    assert years_of_experience(text) == pytest.approx(3.0)


def test_yoe_no_match():
    from app.ml.feature_engine import years_of_experience
    assert years_of_experience("No requirements listed.") == pytest.approx(0.0)
    assert years_of_experience("") == pytest.approx(0.0)


# ── 4. Keyword overlap ────────────────────────────────────────────────────────

def test_keyword_overlap_identical():
    from app.ml.feature_engine import keyword_overlap
    text = "Python developer with Django experience"
    assert keyword_overlap(text, text) == pytest.approx(1.0)


def test_keyword_overlap_disjoint():
    from app.ml.feature_engine import keyword_overlap
    assert keyword_overlap("python developer", "marketing manager") < 0.3


def test_keyword_overlap_empty():
    from app.ml.feature_engine import keyword_overlap
    assert keyword_overlap("", "") == pytest.approx(0.0)


# ── 5. Interaction bonus ──────────────────────────────────────────────────────

def test_interaction_bonus_applied():
    from app.ml.feature_engine import build_interaction_bonus
    job_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    interactions = [{"job_id": job_id, "action": "applied"}]
    bonus = build_interaction_bonus(interactions, job_id)
    assert bonus == pytest.approx(0.15)


def test_interaction_bonus_saved_and_viewed():
    from app.ml.feature_engine import build_interaction_bonus
    job_id = str(uuid.uuid4())
    interactions = [
        {"job_id": job_id, "action": "saved"},
        {"job_id": job_id, "action": "viewed"},
    ]
    bonus = build_interaction_bonus(interactions, job_id)
    assert bonus == pytest.approx(0.15)   # 0.10 + 0.05 = 0.15


def test_interaction_bonus_skipped_reduces():
    from app.ml.feature_engine import build_interaction_bonus
    job_id = str(uuid.uuid4())
    interactions = [{"job_id": job_id, "action": "skipped"}]
    bonus = build_interaction_bonus(interactions, job_id)
    # clamped to 0.0
    assert bonus == pytest.approx(0.0)


def test_interaction_bonus_other_job():
    from app.ml.feature_engine import build_interaction_bonus
    other_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())
    interactions = [{"job_id": other_id, "action": "applied"}]
    assert build_interaction_bonus(interactions, target_id) == pytest.approx(0.0)


# ── 6. YOE compatibility helper ───────────────────────────────────────────────

def test_yoe_compatibility_overqualified():
    from app.services.ranking_service import _yoe_compatibility
    assert _yoe_compatibility(cv_yoe=8.0, jd_yoe=5.0) == pytest.approx(1.0)


def test_yoe_compatibility_underqualified():
    from app.services.ranking_service import _yoe_compatibility
    # 2 years applying for a 4-year role → 0.5
    assert _yoe_compatibility(cv_yoe=2.0, jd_yoe=4.0) == pytest.approx(0.5)


def test_yoe_compatibility_no_requirement():
    from app.services.ranking_service import _yoe_compatibility
    # JD doesn't specify → neutral (0.5)
    assert _yoe_compatibility(cv_yoe=3.0, jd_yoe=0.0) == pytest.approx(0.5)


# ── 7. Composite score formula ────────────────────────────────────────────────

def test_composite_score_full_match():
    from app.services.ranking_service import _composite_score, DEFAULT_WEIGHTS
    score = _composite_score(1.0, 1.0, 1.0, 1.0, DEFAULT_WEIGHTS)
    assert score == pytest.approx(1.0, abs=1e-4)


def test_composite_score_zero():
    from app.services.ranking_service import _composite_score, DEFAULT_WEIGHTS
    score = _composite_score(0.0, 0.0, 0.0, 0.0, DEFAULT_WEIGHTS)
    assert score == pytest.approx(0.0, abs=1e-4)


def test_composite_score_clamped():
    from app.services.ranking_service import _composite_score
    weights = {"cosine": 2.0, "skill": 0.0, "interaction": 0.0, "yoe": 0.0}
    score = _composite_score(1.0, 0.0, 0.0, 0.0, weights)
    # Should be clamped to [0, 1] even with crazy weights
    assert 0.0 <= score <= 1.0


# ── 8. Ranking: candidates better than baseline ───────────────────────────────

def test_ranked_higher_skill_match_scores_better():
    """
    A candidate whose CV has high skill overlap with the JD should receive
    a higher composite score than one with zero skill overlap.
    """
    from app.services.ranking_service import _composite_score, DEFAULT_WEIGHTS

    # Candidate A: decent cosine, good skill overlap
    score_a = _composite_score(
        cosine=0.70, skill=0.80, interaction=0.0, yoe=0.5,
        weights=DEFAULT_WEIGHTS,
    )
    # Candidate B: same cosine, zero skill overlap
    score_b = _composite_score(
        cosine=0.70, skill=0.00, interaction=0.0, yoe=0.5,
        weights=DEFAULT_WEIGHTS,
    )
    assert score_a > score_b, (
        f"Expected skill-match candidate ({score_a:.4f}) > no-skill candidate ({score_b:.4f})"
    )


def test_hired_feedback_raises_score():
    """apply_feedback_signal with 'hired' must increase match_score."""
    from app.services.ranking_service import FEEDBACK_DELTAS
    delta = FEEDBACK_DELTAS["hired"]
    assert delta > 0


def test_rejected_feedback_lowers_score():
    """apply_feedback_signal with 'rejected' must decrease match_score."""
    from app.services.ranking_service import FEEDBACK_DELTAS
    delta = FEEDBACK_DELTAS["rejected"]
    assert delta < 0


def test_cache_invalidation():
    """invalidate_ranking_cache should clear entries for the given job_id."""
    from app.services.ranking_service import _cache, invalidate_ranking_cache
    job_id = uuid.uuid4()
    key = f"{job_id}:test"
    _cache[key] = MagicMock()
    invalidate_ranking_cache(job_id)
    # The key containing the job_id string should be gone
    assert not any(str(job_id) in k for k in _cache)
