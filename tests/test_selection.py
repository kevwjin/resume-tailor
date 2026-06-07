import pytest

from resume_tailor.models import Profile
from resume_tailor.selection import ExplicitSelection, ExplicitSkillSelection, SelectionLoadError, build_resume_selection


def profile() -> Profile:
    return Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "courses": {"select": "Distributed Systems, [Computer Networks]"},
            "projects": {
                "select": "[transport | database]",
                "items": [
                    {"id": "transport", "title": "Transport"},
                    {"id": "database", "title": "Database"},
                ],
            },
            "research": {
                "select": "paper",
                "items": [{"id": "paper", "title": "Paper"}],
            },
            "skills": [
                {"id": "languages", "title": "Languages", "items": "Python, [Go], SQL"},
            ],
        }
    )


def test_build_resume_selection_resolves_ids_and_skill_items() -> None:
    selection = build_resume_selection(
        profile(),
        ExplicitSelection(
            courses=["distributed_systems", "Computer Networks"],
            projects=["transport"],
            research=["paper"],
            skills=[ExplicitSkillSelection(category="Languages", items=["Python", "Go"])],
        ),
    )

    assert selection.courses == ["Distributed Systems", "Computer Networks"]
    assert [item.id for item in selection.projects] == ["transport"]
    assert [item.id for item in selection.research] == ["paper"]
    assert selection.skills[0].category == "Languages"
    assert selection.skills[0].items == ["Python", "Go"]
    assert selection.compile_attempts == 1


def test_build_resume_selection_includes_pinned_research_when_omitted() -> None:
    selection = build_resume_selection(profile(), ExplicitSelection(research=[]))

    assert [item.id for item in selection.research] == ["paper"]


def test_build_resume_selection_dedupes_explicit_pinned_research() -> None:
    selection = build_resume_selection(profile(), ExplicitSelection(research=["paper"]))

    assert [item.id for item in selection.research] == ["paper"]


def test_build_resume_selection_rejects_unknown_project() -> None:
    with pytest.raises(SelectionLoadError, match="Unknown project: missing"):
        build_resume_selection(profile(), ExplicitSelection(projects=["missing"]))


def test_build_resume_selection_rejects_unknown_skill_item() -> None:
    with pytest.raises(SelectionLoadError, match="Unknown skill item"):
        build_resume_selection(
            profile(),
            ExplicitSelection(
                skills=[ExplicitSkillSelection(category="Languages", items=["Rust"])],
            ),
        )
