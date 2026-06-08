from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Sequence, TypeVar

from resume_tailor.models import Position, Profile, Project, Research, SkillItem, slugify
from resume_tailor.ranking import RankedItem

T = TypeVar("T", Project, Research)


@dataclass
class SkillSelection:
    category: str
    items: list[str] = field(default_factory=list)


@dataclass
class ResumeSelection:
    courses: list[str] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    research: list[Research] = field(default_factory=list)
    skills: list[SkillSelection] = field(default_factory=list)
    pruned_ids: list[str] = field(default_factory=list)
    compile_attempts: int = 0
    needs_review: str | None = None

    def without_item(self, item_id: str) -> "ResumeSelection":
        return replace(
            self,
            projects=[item for item in self.projects if item.id != item_id],
            research=[item for item in self.research if item.id != item_id],
            pruned_ids=[*self.pruned_ids, item_id],
        )

    def without_skill(self, category: str, title: str, item_id: str) -> "ResumeSelection":
        skills = []
        for skill in self.skills:
            if skill.category == category:
                skills.append(replace(skill, items=[item for item in skill.items if item != title]))
            else:
                skills.append(skill)
        return replace(
            self,
            skills=[skill for skill in skills if skill.items],
            pruned_ids=[*self.pruned_ids, item_id],
        )

    def with_skills(self, skills: list[SkillSelection]) -> "ResumeSelection":
        return replace(self, skills=skills)


def select_resume(
    profile: Profile,
    ranked_courses: Sequence[RankedItem],
    ranked_projects: Sequence[RankedItem],
    ranked_research: Sequence[RankedItem],
    ranked_skill_items: Sequence[RankedItem],
) -> ResumeSelection:
    courses = select_courses(profile, ranked_courses)
    projects = order_with_pins(profile.projects, ranked_projects)
    research = order_with_pins(profile.research, ranked_research)
    skills = select_skills(profile, ranked_skill_items)
    return ResumeSelection(
        courses=courses,
        projects=projects,
        research=research,
        skills=dedupe_skill_selections(skills),
        pruned_ids=[],
    )


def select_courses(profile: Profile, ranked_courses: Sequence[RankedItem]) -> list[str]:
    ranked_by_id = {rank.item.id: rank.item for rank in ranked_courses}
    pinned = [course for course in profile.courses if course.pos == Position.PIN]
    required = [ranked_by_id[rank.item.id] for rank in ranked_courses if rank.item.pos == Position.REQ]
    optional = [ranked_by_id[rank.item.id] for rank in ranked_courses if rank.item.pos == Position.OPT]

    selected = [course.title for course in pinned]
    for course in required:
        if course.title not in selected:
            selected.append(course.title)

    for course in optional:
        if course.title not in selected:
            selected.append(course.title)
    return selected


def select_skills(
    profile: Profile,
    ranked_skill_items: Sequence[RankedItem],
    max_optional_per_category: int | None = None,
    allowed_skill_ids: set[str] | None = None,
) -> list[SkillSelection]:
    ranked_by_category: dict[str, list[SkillItem]] = {}
    for rank in ranked_skill_items:
        item = rank.item
        if isinstance(item, SkillItem):
            ranked_by_category.setdefault(item.category, []).append(item)

    selected: list[SkillSelection] = []
    for skill in profile.skills:
        category = skill.category or skill.title
        max_optional = max(0, max_optional_per_category or 0)
        ranked_optional = [
            item.title
            for item in ranked_by_category.get(category, [])
            if item.title in skill.items and skill.item_positions.get(item.title, Position.PIN) == Position.OPT
        ]
        if allowed_skill_ids is not None:
            selected_optional = {
                item
                for item in ranked_optional
                if f"{slugify(category)}__{slugify(item)}" in allowed_skill_ids
            }
        else:
            selected_optional = set(ranked_optional[:max_optional])
        items: list[str] = []
        for item in skill.items:
            item_pos = skill.item_positions.get(item, Position.PIN)
            if item_pos in {Position.PIN, Position.REQ}:
                items.append(item)
            elif item in selected_optional:
                items.append(item)
        items = dedupe_keep_order(items)
        if items:
            selected.append(SkillSelection(category=category, items=items))
    return selected


def order_with_pins(items: Sequence[T], ranked_items: Sequence[RankedItem]) -> list[T]:
    ranked_map = {rank.item.id: rank.item for rank in ranked_items}
    non_pinned = [
        ranked_map[rank.item.id]
        for rank in ranked_items
        if rank.item.pos in {Position.REQ, Position.OPT}
    ]
    non_pinned_iter = iter(non_pinned)
    ordered: list[T] = []

    for original in items:
        if original.pos == Position.PIN:
            ordered.append(original)
        else:
            try:
                ordered.append(next(non_pinned_iter))
            except StopIteration:
                break

    ordered.extend(non_pinned_iter)
    return dedupe_items(ordered)


def lowest_ranked_optional_id(
    selection: ResumeSelection,
    ranked_items: Sequence[RankedItem],
) -> str | None:
    present_ids = selected_evidence_ids(selection)
    candidates = [
        rank
        for rank in ranked_items
        if rank.item.id in present_ids and rank.item.pos == Position.OPT
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda rank: (rank.score, -rank.index)).item.id


def lowest_ranked_evidence_id(selection: ResumeSelection, ranked_items: Sequence[RankedItem]) -> str | None:
    present_ids = selected_evidence_ids(selection)
    candidates = [rank for rank in ranked_items if rank.item.id in present_ids]
    if not candidates:
        return None
    return min(candidates, key=lambda rank: (rank.keyword_score, rank.score, -rank.index)).item.id


def selected_evidence_ids(selection: ResumeSelection) -> set[str]:
    return {item.id for item in [*selection.projects, *selection.research]}


def dedupe_keep_order(values: Sequence[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def dedupe_skill_selections(values: Sequence[SkillSelection]) -> list[SkillSelection]:
    seen = set()
    result = []
    for value in values:
        if value.category and value.category not in seen:
            seen.add(value.category)
            result.append(value)
    return result


def dedupe_items(items: Sequence[T]) -> list[T]:
    seen = set()
    result = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            result.append(item)
    return result
