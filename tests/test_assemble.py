import pytest

from resume_tailor.assemble import (
    ResumeSelection,
    SkillSelection,
    lowest_ranked_evidence_id,
    lowest_ranked_optional_id,
    select_courses,
    select_resume,
    select_skills,
)
from resume_tailor.models import Course, Position, Profile, SkillItem, skill_candidates
from resume_tailor.ranking import RankedItem


def ranked(item, score: float, index: int = 0) -> RankedItem:
    return RankedItem(item=item, score=score, semantic_score=score, keyword_score=0, index=index)


def ranked_skill(item: SkillItem, score: float, index: int = 0) -> RankedItem:
    return RankedItem(item=item, score=score, semantic_score=score, keyword_score=0, index=index)


def test_courses_parse_optional_group_string() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "courses": "[Databases | Computer Networks | Machine Learning]",
        }
    )

    assert [course.title for course in profile.courses] == [
        "Databases",
        "Computer Networks",
        "Machine Learning",
    ]
    assert {course.pos for course in profile.courses} == {Position.OPT}


def test_courses_parse_section_select_string() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "courses": {"select": "Distributed Systems, [Databases | Machine Learning]"},
        }
    )

    assert [course.title for course in profile.courses] == [
        "Distributed Systems",
        "Databases",
        "Machine Learning",
    ]
    assert [course.pos for course in profile.courses] == [
        Position.PIN,
        Position.OPT,
        Position.OPT,
    ]


def test_courses_pin_req_then_optional_fit() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "layout": {"course_line_max_chars": 24},
            "courses": [
                {"id": "a", "title": "Pinned", "pos": "pin"},
                {"id": "b", "title": "Required", "pos": "req"},
                {"id": "c", "title": "Optional Long"},
                {"id": "d", "title": "Opt"},
            ],
        }
    )
    courses = [ranked(course, 1.0 - index / 10, index) for index, course in enumerate(profile.courses)]
    warnings: list[str] = []
    assert select_courses(profile, courses, warnings) == ["Pinned", "Required", "Opt"]


def test_courses_fill_by_rank_without_pins() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "layout": {"course_line_max_chars": 34},
            "courses": [
                {"id": "ui", "title": "User Interface Design"},
                {"id": "db", "title": "Databases"},
                {"id": "net", "title": "Computer Networks"},
            ],
        }
    )
    rankings = [
        ranked(profile.courses[1], 0.9, 0),
        ranked(profile.courses[2], 0.8, 1),
        ranked(profile.courses[0], 0.7, 2),
    ]

    warnings: list[str] = []

    assert select_courses(profile, rankings, warnings) == ["Databases", "Computer Networks"]


def test_skills_parse_and_rank_optional_group() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "layout": {"max_optional_skills_per_category": 2},
            "skills": [
                {
                    "id": "languages",
                    "title": "Languages",
                    "items": "Python, Java, C/C++, [Go | JavaScript | Swift], HTML, CSS, SQL",
                }
            ],
        }
    )
    candidates = skill_candidates(profile)
    rankings = [
        ranked_skill(next(item for item in candidates if item.title == "JavaScript"), 0.9, 0),
        ranked_skill(next(item for item in candidates if item.title == "Go"), 0.8, 1),
        ranked_skill(next(item for item in candidates if item.title == "Swift"), 0.7, 2),
    ]

    selection = select_skills(profile, rankings)

    assert selection[0].category == "Languages"
    assert selection[0].items == [
        "Python",
        "Java",
        "C/C++",
        "Go",
        "JavaScript",
        "HTML",
        "CSS",
        "SQL",
    ]


def test_skills_parse_commas_inside_parentheses() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "skills": [
                {
                    "id": "tools",
                    "title": "Tools",
                    "items": "AWS (ALB, EC2, SQS, S3, DynamoDB), Terraform, Git",
                }
            ],
        }
    )

    assert profile.skills[0].items == [
        "AWS (ALB, EC2, SQS, S3, DynamoDB)",
        "Terraform",
        "Git",
    ]


def test_select_resume_keeps_skill_selections() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "layout": {"max_optional_skills_per_category": 1},
            "skills": [{"id": "languages", "title": "Languages", "items": "Python, [Go]"}],
        }
    )
    candidates = skill_candidates(profile)
    selection = select_resume(profile, [], [], [], [ranked_skill(candidates[0], 0.9)])

    assert selection.skills[0].category == "Languages"
    assert selection.skills[0].items == ["Python", "Go"]


def test_select_skills_preserves_multiple_optional_group_positions() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "layout": {"max_optional_skills_per_category": 3},
            "skills": [
                {
                    "id": "tools",
                    "title": "Tools",
                    "items": "Skill1, Skill2, [Skill3 | Skill4], Skill5, [Skill6]",
                }
            ],
        }
    )
    candidates = skill_candidates(profile)
    rankings = [
        ranked_skill(next(item for item in candidates if item.title == "Skill6"), 0.9, 0),
        ranked_skill(next(item for item in candidates if item.title == "Skill4"), 0.8, 1),
        ranked_skill(next(item for item in candidates if item.title == "Skill3"), 0.7, 2),
    ]

    selection = select_skills(profile, rankings)

    assert selection[0].items == ["Skill1", "Skill2", "Skill3", "Skill4", "Skill5", "Skill6"]


def test_projects_parse_section_select_with_items() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "projects": {
                "select": "pinned, [optional]",
                "items": [
                    {"id": "optional", "title": "Optional"},
                    {"id": "pinned", "title": "Pinned"},
                    {"id": "unlisted", "title": "Unlisted"},
                ],
            },
        }
    )

    assert [project.id for project in profile.projects] == ["pinned", "optional", "unlisted"]
    assert [project.pos for project in profile.projects] == [Position.OPT, Position.OPT, Position.OPT]


def test_research_preserves_abstract_for_ranking_text() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "research": {
                "select": "[paper]",
                "items": [
                    {
                        "id": "paper",
                        "title": "Paper",
                        "abstract": "Resource leaks can lead to system crashes.",
                    }
                ],
            },
        }
    )

    assert profile.research[0].abstract == "Resource leaks can lead to system crashes."
    assert "Resource leaks" in profile.research[0].text_for_rank()
    assert profile.research[0].pos == Position.OPT


def test_select_resume_orders_ranked_research() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "research": {
                "select": "[paper_a | paper_b]",
                "items": [
                    {"id": "paper_a", "title": "Paper A"},
                    {"id": "paper_b", "title": "Paper B"},
                ],
            },
        }
    )

    selection = select_resume(
        profile,
        [],
        [],
        [ranked(profile.research[1], 0.9, 0), ranked(profile.research[0], 0.1, 1)],
        [],
    )

    assert [item.id for item in selection.research] == ["paper_b", "paper_a"]


def test_section_select_rejects_unknown_item_id() -> None:
    with pytest.raises(ValueError, match="unknown item id"):
        Profile.model_validate(
            {
                "personal": {"name": "Example User"},
                "projects": {"select": "missing", "items": [{"id": "present", "title": "Present"}]},
            }
        )


def test_lowest_ranked_optional_skips_required_and_pinned() -> None:
    opt = Course(id="opt", title="Optional")
    req = Course(id="req", title="Required", pos=Position.REQ)
    ranks = [ranked(opt, 0.1), ranked(req, 0.0)]
    selection = type("Selection", (), {"projects": [opt, req], "research": []})()
    assert lowest_ranked_optional_id(selection, ranks) == "opt"


def test_lowest_ranked_optional_can_prune_research() -> None:
    project = Course(id="project", title="Project")
    research = Course(id="research", title="Research")
    selection = ResumeSelection(projects=[project], research=[research])
    ranks = [ranked(project, 0.8, 0), ranked(research, 0.1, 1)]

    assert lowest_ranked_optional_id(selection, ranks) == "research"


def test_lowest_ranked_evidence_can_prune_pinned_research_as_last_resort() -> None:
    high = Course(id="high", title="High", pos=Position.PIN)
    low = Course(id="low", title="Low", pos=Position.PIN)
    selection = ResumeSelection(projects=[high], research=[low])
    ranks = [
        RankedItem(item=high, score=0.8, semantic_score=0.8, keyword_score=0.5, index=0),
        RankedItem(item=low, score=0.9, semantic_score=0.9, keyword_score=0.0, index=1),
    ]

    assert lowest_ranked_evidence_id(selection, ranks) == "low"


def test_without_skill_removes_skill_and_tracks_pruned_id() -> None:
    selection = ResumeSelection(skills=[SkillSelection(category="Languages", items=["Python", "Go"])])

    updated = selection.without_skill("Languages", "Go", "languages__go")

    assert updated.skills[0].items == ["Python"]
    assert updated.pruned_ids == ["languages__go"]
