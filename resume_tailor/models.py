"""Pydantic schemas for validating and normalizing resume profile data."""

from __future__ import annotations

from enum import StrEnum
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Position(StrEnum):
    OPT = "opt"
    REQ = "req"
    PIN = "pin"


class Link(BaseModel):
    label: str | None = None
    url: str


class HeaderLink(BaseModel):
    label: str
    url: str


class BaseItem(BaseModel):
    id: str
    title: str = ""
    pos: Position = Position.OPT
    tags: list[str] = Field(default_factory=list)
    rank_text: str | None = None

    def text_for_rank(self) -> str:
        parts = [self.title, self.rank_text or "", " ".join(self.tags)]
        return " ".join(part for part in parts if part).strip()


class Course(BaseItem):
    name: str | None = None

    @model_validator(mode="after")
    def default_title_from_name(self) -> "Course":
        if self.name and self.title == "":
            self.title = self.name
        if self.title == "":
            self.title = self.id.replace("_", " ").title()
        return self


class Project(BaseItem):
    url: str | None = None
    links: list[Link] = Field(default_factory=list)
    tech: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)

    def text_for_rank(self) -> str:
        return " ".join(
            part
            for part in [
                super().text_for_rank(),
                " ".join(self.tech),
                " ".join(self.bullets),
                self.url or "",
            ]
            if part
        )

    def all_urls(self) -> list[str]:
        urls = []
        if self.url:
            urls.append(self.url)
        urls.extend(link.url for link in self.links)
        return urls


class Research(Project):
    venue: str | None = None
    authors: str | None = None
    abstract: str | None = None

    def text_for_rank(self) -> str:
        return " ".join([super().text_for_rank(), self.venue or "", self.authors or "", self.abstract or ""])


class Skill(BaseItem):
    category: str | None = None
    items: list[str] = Field(default_factory=list)
    item_positions: dict[str, Position] = Field(default_factory=dict)

    def text_for_rank(self) -> str:
        return " ".join([super().text_for_rank(), self.category or "", " ".join(self.items)])


class SkillItem(BaseItem):
    category: str

    def text_for_rank(self) -> str:
        return " ".join([super().text_for_rank(), self.category])


class Education(BaseModel):
    id: str
    school: str
    degree: str | None = None
    location: str | None = None
    dates: str | None = None
    details: list[str] = Field(default_factory=list)
    pos: Position = Position.PIN


class Experience(BaseModel):
    id: str
    company: str
    title: str
    location: str | None = None
    dates: str | None = None
    bullets: list[str] = Field(default_factory=list)
    pos: Literal[Position.PIN] = Position.PIN

    def text_for_rank(self) -> str:
        return " ".join([self.company, self.title, " ".join(self.bullets)])


class Personal(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    citizenship: str | None = None
    website: str | None = None
    website_label: str | None = None
    links: list[HeaderLink] = Field(default_factory=list)
    github: str | None = None
    linkedin: str | None = None


class ForgejoConfig(BaseModel):
    host: str | None = None
    code: str = ""
    note_template: str = (
        r"\faExclamationCircle\hspace{0.5em}"
        r"Enter code \textbf{{code}} to access close-sourced repositories"
    )


class LayoutConfig(BaseModel):
    max_project_tech_items: int = 6
    max_compile_attempts: int = 50


class Profile(BaseModel):
    personal: Personal
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    courses: list[Course] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    research: list[Research] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    forgejo: ForgejoConfig = Field(default_factory=ForgejoConfig)
    layout: LayoutConfig = Field(default_factory=LayoutConfig)

    @field_validator("courses", mode="before")
    @classmethod
    def normalize_courses(cls, value: object) -> object:
        if isinstance(value, dict) and isinstance(value.get("select"), str):
            value = value["select"]
        if isinstance(value, str):
            return [
                {"id": slugify(item), "title": item, "pos": pos}
                for item, pos in parse_item_expr(value, bracket_pos=Position.OPT)
            ]
        if isinstance(value, list):
            normalized = []
            for item in value:
                if isinstance(item, str):
                    normalized.append({"id": item.lower().replace(" ", "_"), "title": item})
                else:
                    normalized.append(item)
            return normalized
        return value

    @field_validator("projects", mode="before")
    @classmethod
    def normalize_project_items(cls, value: object) -> object:
        if isinstance(value, dict):
            items = value.get("items", [])
            select = value.get("select")
            if isinstance(select, str):
                return apply_selection_expr(items, select, bracket_pos=Position.OPT, bare_pos=Position.OPT)
            return items
        return value

    @field_validator("research", mode="before")
    @classmethod
    def normalize_research_items(cls, value: object) -> object:
        if isinstance(value, dict):
            items = value.get("items", [])
            select = value.get("select")
            if isinstance(select, str):
                return apply_selection_expr(items, select, bracket_pos=Position.OPT, bare_pos=Position.PIN)
            return items
        return value

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_skills(cls, value: object) -> object:
        if isinstance(value, list):
            normalized = []
            for skill in value:
                if isinstance(skill, dict) and isinstance(skill.get("items"), str):
                    items_with_pos = parse_item_expr(skill["items"], bracket_pos=Position.OPT)
                    normalized.append(
                        {
                            **skill,
                            "items": [item for item, _ in items_with_pos],
                            "item_positions": {item: pos for item, pos in items_with_pos},
                        }
                    )
                else:
                    normalized.append(skill)
            return normalized
        return value


def skill_candidates(profile: Profile) -> list[SkillItem]:
    candidates: list[SkillItem] = []
    for skill in profile.skills:
        category = skill.category or skill.title
        for item in skill.items:
            if skill.item_positions.get(item, Position.PIN) == Position.OPT:
                candidates.append(
                    SkillItem(
                        id=f"{slugify(category)}__{slugify(item)}",
                        title=item,
                        category=category,
                    )
                )
    return candidates


def apply_selection_expr(
    items: object,
    expr: str,
    bracket_pos: Position = Position.OPT,
    bare_pos: Position = Position.PIN,
) -> object:
    if not isinstance(items, list):
        return items

    by_id = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            by_id[item["id"]] = item

    ordered = []
    seen = set()
    for item_id, pos in parse_item_expr(expr, bracket_pos=bracket_pos, bare_pos=bare_pos):
        if item_id not in by_id:
            raise ValueError(f"selection references unknown item id: {item_id}")
        ordered.append({**by_id[item_id], "pos": pos})
        seen.add(item_id)

    for item in items:
        if isinstance(item, dict) and item.get("id") in seen:
            continue
        ordered.append(item)

    return ordered


def parse_item_expr(
    expr: str,
    bracket_pos: Position,
    bare_pos: Position = Position.PIN,
) -> list[tuple[str, Position]]:
    items: list[tuple[str, Position]] = []
    for segment in split_top_level(expr, ","):
        segment = segment.strip()
        if not segment:
            continue
        if segment.startswith("[") and segment.endswith("]"):
            for item in split_top_level(segment[1:-1], "|"):
                title = item.strip()
                if title:
                    items.append((title, bracket_pos))
        else:
            items.append((segment, bare_pos))
    return items


def split_top_level(value: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    bracket_depth = 0
    paren_depth = 0
    start = 0
    for index, character in enumerate(value):
        if character == "[":
            bracket_depth += 1
        elif character == "]":
            bracket_depth = max(0, bracket_depth - 1)
        elif character == "(":
            paren_depth += 1
        elif character == ")":
            paren_depth = max(0, paren_depth - 1)
        elif character == delimiter and bracket_depth == 0 and paren_depth == 0:
            parts.append(value[start:index])
            start = index + 1
    parts.append(value[start:])
    return parts


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "item"
