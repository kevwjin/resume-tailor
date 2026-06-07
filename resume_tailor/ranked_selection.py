from __future__ import annotations

from pathlib import Path
from typing import Sequence

import yaml
from pydantic import BaseModel, Field, ValidationError

from resume_tailor.assemble import ResumeSelection, SkillSelection, dedupe_keep_order
from resume_tailor.models import Course, Position, Profile, Project, Research


class RankedSelectionLoadError(ValueError):
    pass


class RankedSelection(BaseModel):
    evidence: list[str] = Field(default_factory=list)
    courses: list[str] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)


class RankedCandidatePool(BaseModel):
    evidence: list[Project | Research]
    courses: list[Course]
    skill_choices_by_category: dict[str, list[str]]

    model_config = {"arbitrary_types_allowed": True}


def load_ranked_selection(path: Path) -> RankedSelection:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RankedSelectionLoadError(f"Ranking not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise RankedSelectionLoadError(f"Invalid YAML in {path}: {exc}") from exc

    if raw is None:
        raise RankedSelectionLoadError(f"Ranking is empty: {path}")

    try:
        return RankedSelection.model_validate(raw)
    except ValidationError as exc:
        raise RankedSelectionLoadError(str(exc)) from exc


def validate_ranked_selection(profile: Profile, ranking: RankedSelection) -> RankedCandidatePool:
    evidence_by_id = {item.id: item for item in [*profile.projects, *profile.research]}
    optional_evidence_ids = [item.id for item in evidence_by_id.values() if item.pos == Position.OPT]
    validate_complete_order("evidence", ranking.evidence, optional_evidence_ids)

    optional_courses = [course for course in profile.courses if course.pos == Position.OPT]
    course_lookup = course_value_lookup(optional_courses)
    ranked_course_ids = []
    for value in ranking.courses:
        if value not in course_lookup:
            raise RankedSelectionLoadError(f"Unknown optional course: {value}")
        ranked_course_ids.append(course_lookup[value].id)
    validate_complete_order("courses", ranked_course_ids, [course.id for course in optional_courses])

    skill_choices_by_category: dict[str, list[str]] = {}
    skills_by_category = {skill.category or skill.title: skill for skill in profile.skills}
    missing_categories = []
    for category, skill in skills_by_category.items():
        optional_items = [
            item
            for item in skill.items
            if skill.item_positions.get(item, Position.PIN) == Position.OPT
        ]
        if not optional_items:
            continue
        if category not in ranking.skills:
            missing_categories.append(category)
            continue
        validate_complete_order(f"skills.{category}", ranking.skills[category], optional_items)
        skill_choices_by_category[category] = ranking.skills[category]
    if missing_categories:
        raise RankedSelectionLoadError(
            "Missing optional skill ranking for: " + ", ".join(missing_categories)
        )

    known_skill_categories = set(skills_by_category)
    extra_categories = [category for category in ranking.skills if category not in known_skill_categories]
    if extra_categories:
        raise RankedSelectionLoadError(
            "Unknown skill category: " + ", ".join(extra_categories)
        )

    return RankedCandidatePool(
        evidence=[evidence_by_id[item_id] for item_id in ranking.evidence],
        courses=[course_lookup[item_id] for item_id in ranked_course_ids],
        skill_choices_by_category=skill_choices_by_category,
    )


def build_ranked_resume_selection(
    profile: Profile,
    pool: RankedCandidatePool,
    evidence_count: int,
    optional_skill_counts: dict[str, int] | None = None,
) -> ResumeSelection:
    optional_skill_counts = optional_skill_counts or {}
    selected_evidence = pool.evidence[:evidence_count]
    project_ids = {item.id for item in selected_evidence if isinstance(item, Project) and not isinstance(item, Research)}
    research_ids = {item.id for item in selected_evidence if isinstance(item, Research)}

    projects = [
        *[item for item in profile.projects if item.pos in {Position.PIN, Position.REQ}],
        *[item for item in pool.evidence if isinstance(item, Project) and not isinstance(item, Research) and item.id in project_ids],
    ]
    research = [
        *[item for item in profile.research if item.pos in {Position.PIN, Position.REQ}],
        *[item for item in pool.evidence if isinstance(item, Research) and item.id in research_ids],
    ]

    return ResumeSelection(
        courses=select_ranked_courses(profile, pool.courses),
        projects=dedupe_keep_items(projects),
        research=dedupe_keep_items(research),
        skills=select_ranked_skills(profile, pool.skill_choices_by_category, optional_skill_counts),
    )


def select_ranked_courses(profile: Profile, optional_courses: Sequence[Course]) -> list[str]:
    selected = [course.title for course in profile.courses if course.pos in {Position.PIN, Position.REQ}]
    for course in optional_courses:
        candidate = [*selected, course.title]
        if len(", ".join(candidate)) <= profile.layout.course_line_max_chars:
            selected.append(course.title)
    return dedupe_keep_order(selected)


def select_ranked_skills(
    profile: Profile,
    skill_choices_by_category: dict[str, list[str]],
    optional_skill_counts: dict[str, int],
) -> list[SkillSelection]:
    selected = []
    for skill in profile.skills:
        category = skill.category or skill.title
        allowed = set(skill_choices_by_category.get(category, [])[: optional_skill_counts.get(category, 0)])
        items = []
        for item in skill.items:
            item_pos = skill.item_positions.get(item, Position.PIN)
            if item_pos in {Position.PIN, Position.REQ}:
                items.append(item)
            elif item in allowed:
                items.append(item)
        if items:
            selected.append(SkillSelection(category=category, items=dedupe_keep_order(items)))
    return selected


def validate_complete_order(label: str, actual: list[str], expected: list[str]) -> None:
    actual_set = set(actual)
    expected_set = set(expected)
    duplicates = sorted({item for item in actual if actual.count(item) > 1})
    missing = [item for item in expected if item not in actual_set]
    extra = [item for item in actual if item not in expected_set]
    if duplicates:
        raise RankedSelectionLoadError(f"Duplicate {label}: {', '.join(duplicates)}")
    if missing:
        raise RankedSelectionLoadError(f"Missing {label}: {', '.join(missing)}")
    if extra:
        raise RankedSelectionLoadError(f"Unknown {label}: {', '.join(extra)}")


def course_value_lookup(courses: Sequence[Course]) -> dict[str, Course]:
    lookup = {}
    for course in courses:
        lookup[course.id] = course
        lookup[course.title] = course
    return lookup


def dedupe_keep_items(items: Sequence[Project | Research]) -> list:
    seen = set()
    result = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            result.append(item)
    return result
