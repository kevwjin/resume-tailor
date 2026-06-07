from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from resume_tailor.assemble import ResumeSelection, SkillSelection
from resume_tailor.models import Position, Profile


class SelectionLoadError(ValueError):
    pass


class ExplicitSkillSelection(BaseModel):
    category: str
    items: list[str] = Field(default_factory=list)


class ExplicitSelection(BaseModel):
    courses: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    research: list[str] = Field(default_factory=list)
    skills: list[ExplicitSkillSelection] = Field(default_factory=list)


def load_explicit_selection(path: Path) -> ExplicitSelection:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SelectionLoadError(f"Selection not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise SelectionLoadError(f"Invalid YAML in {path}: {exc}") from exc

    if raw is None:
        raise SelectionLoadError(f"Selection is empty: {path}")

    try:
        return ExplicitSelection.model_validate(raw)
    except ValidationError as exc:
        raise SelectionLoadError(str(exc)) from exc


def build_resume_selection(profile: Profile, explicit: ExplicitSelection) -> ResumeSelection:
    return ResumeSelection(
        courses=resolve_courses(profile, explicit.courses),
        projects=resolve_evidence_items("project", profile.projects, explicit.projects),
        research=resolve_evidence_items("research", profile.research, explicit.research),
        skills=resolve_skills(profile, explicit.skills),
        compile_attempts=1,
    )


def resolve_courses(profile: Profile, values: list[str]) -> list[str]:
    by_id = {course.id: course.title for course in profile.courses}
    by_title = {course.title: course.title for course in profile.courses}
    resolved = []
    for value in values:
        if value in by_title:
            resolved.append(by_title[value])
        elif value in by_id:
            resolved.append(by_id[value])
        else:
            raise SelectionLoadError(f"Unknown course: {value}")
    return resolved


def resolve_evidence_items(kind: str, profile_items: list, values: list[str]) -> list:
    by_id = {item.id: item for item in profile_items}
    resolved = [item for item in profile_items if item.pos == Position.PIN]
    seen = {item.id for item in resolved}
    for value in values:
        if value not in by_id:
            raise SelectionLoadError(f"Unknown {kind}: {value}")
        if value not in seen:
            resolved.append(by_id[value])
            seen.add(value)
    return resolved


def resolve_skills(profile: Profile, values: list[ExplicitSkillSelection]) -> list[SkillSelection]:
    skills_by_category = {skill.category or skill.title: skill for skill in profile.skills}
    resolved = []
    for value in values:
        if value.category not in skills_by_category:
            raise SelectionLoadError(f"Unknown skill category: {value.category}")
        available = set(skills_by_category[value.category].items)
        missing = [item for item in value.items if item not in available]
        if missing:
            raise SelectionLoadError(
                f"Unknown skill item(s) in {value.category}: {', '.join(missing)}"
            )
        resolved.append(SkillSelection(category=value.category, items=value.items))
    return resolved
