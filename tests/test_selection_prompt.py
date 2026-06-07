from resume_tailor.models import Profile
from resume_tailor.selection_prompt import build_selection_prompt


def test_selection_prompt_includes_inventory_and_skill_items() -> None:
    profile = Profile.model_validate(
        {
            "personal": {"name": "Example User"},
            "courses": {"select": "Distributed Systems, [Computer Networks]"},
            "projects": {
                "select": "[tool]",
                "items": [
                    {
                        "id": "tool",
                        "title": "Tool",
                        "tech": ["React", "FastAPI"],
                        "bullets": ["Built an internal tool"],
                    }
                ],
            },
            "research": {
                "select": "[paper]",
                "items": [
                    {
                        "id": "paper",
                        "title": "Paper",
                        "abstract": "LLM software engineering research.",
                    }
                ],
            },
            "skills": [
                {
                    "id": "frameworks",
                    "title": "Frameworks & Databases",
                    "items": "React, FastAPI, PostgreSQL",
                }
            ],
        }
    )

    prompt = build_selection_prompt(profile, "Build React tools.")

    assert "Build React tools." in prompt
    assert "`tool` - Tool" in prompt
    assert "Built an internal tool" in prompt
    assert "`paper` - Paper" in prompt
    assert "LLM software engineering research." in prompt
    assert "### Frameworks & Databases" in prompt
    assert "- React (pin)" in prompt
