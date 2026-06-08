import pytest

from resume_tailor.models import Profile
from resume_tailor.ranked_selection import (
    RankedSelection,
    RankedSelectionLoadError,
    build_ranked_resume_selection,
    validate_ranked_selection,
)


def profile() -> Profile:
    return Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "courses": {"select": "Distributed Systems, [Databases | Computer Networks]"},
            "projects": {
                "select": "[tool | network]",
                "items": [
                    {"id": "tool", "title": "Tool"},
                    {"id": "network", "title": "Network"},
                ],
            },
            "research": {
                "select": "[paper]",
                "items": [{"id": "paper", "title": "Paper"}],
            },
            "skills": [
                {
                    "id": "languages",
                    "title": "Languages",
                    "items": "Python, [Go | JavaScript], SQL",
                },
                {
                    "id": "frameworks",
                    "title": "Frameworks & Databases",
                    "items": "React, [FastAPI | PostgreSQL], Jupyter Notebook",
                },
            ],
        }
    )


def valid_ranking() -> RankedSelection:
    return RankedSelection(
        evidence=["paper", "tool", "network"],
        courses=["Computer Networks", "databases"],
        skills={
            "Languages": ["JavaScript", "Go"],
            "Frameworks & Databases": ["FastAPI", "PostgreSQL"],
        },
    )


def test_validate_ranked_selection_requires_complete_optional_rankings() -> None:
    pool = validate_ranked_selection(profile(), valid_ranking())

    assert [item.id for item in pool.evidence] == ["paper", "tool", "network"]
    assert [course.id for course in pool.courses] == ["computer_networks", "databases"]
    assert pool.skill_choices_by_category == {
        "Languages": ["JavaScript", "Go"],
        "Frameworks & Databases": ["FastAPI", "PostgreSQL"],
    }


def test_validate_ranked_selection_rejects_missing_optional_evidence() -> None:
    ranking = valid_ranking()
    ranking.evidence = ["paper", "tool"]

    with pytest.raises(RankedSelectionLoadError, match="Missing evidence: network"):
        validate_ranked_selection(profile(), ranking)


def test_validate_ranked_selection_rejects_duplicate_optional_skill() -> None:
    ranking = valid_ranking()
    ranking.skills["Languages"] = ["Go", "Go"]

    with pytest.raises(RankedSelectionLoadError, match="Duplicate skills.Languages: Go"):
        validate_ranked_selection(profile(), ranking)


def test_build_ranked_resume_selection_uses_prefix_counts_and_pinned_items() -> None:
    pool = validate_ranked_selection(profile(), valid_ranking())
    selection = build_ranked_resume_selection(
        profile(),
        pool,
        evidence_count=2,
        optional_skill_counts={"Languages": 2, "Frameworks & Databases": 0},
    )

    assert [item.id for item in selection.research] == ["paper"]
    assert [item.id for item in selection.projects] == ["tool"]
    assert selection.courses == ["Distributed Systems", "Computer Networks", "Databases"]
    assert selection.skills[0].items == ["Python", "Go", "JavaScript", "SQL"]
    assert selection.skills[1].items == ["React", "Jupyter Notebook"]


def test_build_ranked_resume_selection_uses_course_prefix_count() -> None:
    pool = validate_ranked_selection(profile(), valid_ranking())
    selection = build_ranked_resume_selection(
        profile(),
        pool,
        evidence_count=0,
        optional_course_count=1,
    )

    assert selection.courses == ["Distributed Systems", "Computer Networks"]


def test_build_ranked_resume_selection_preserves_optional_skill_positions() -> None:
    custom_profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "skills": [
                {
                    "id": "tools",
                    "title": "Tools",
                    "items": "Skill1, Skill2, [Skill3 | Skill4], Skill5, [Skill6]",
                }
            ],
        }
    )
    ranking = RankedSelection(
        evidence=[],
        courses=[],
        skills={"Tools": ["Skill6", "Skill4", "Skill3"]},
    )
    pool = validate_ranked_selection(custom_profile, ranking)

    selection = build_ranked_resume_selection(
        custom_profile,
        pool,
        evidence_count=0,
        optional_skill_counts={"Tools": 1},
    )

    assert selection.skills[0].items == ["Skill1", "Skill2", "Skill5", "Skill6"]
