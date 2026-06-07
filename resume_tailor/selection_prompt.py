from __future__ import annotations

from resume_tailor.models import Profile


def build_selection_prompt(profile: Profile, job_text: str) -> str:
    lines = [
        "# Resume Selection Prompt",
        "",
        "Use the software-resume-tailor skill to rank every optional resume item for this job.",
        "Return a complete ranking YAML with this schema:",
        "",
        "```yaml",
        "evidence:",
        "  - project_or_research_id",
        "courses:",
        "  - optional_course_id_or_title",
        "skills:",
        "  Languages:",
        "    - optional_skill_item",
        "```",
        "",
        "Rules:",
        "- `evidence` must include every optional project and research id exactly once.",
        "- `courses` must include every optional course exactly once, using either id or title.",
        "- `skills` must include every optional skill item exactly once under each category.",
        "- Do not include pinned items in the ranking. The CLI includes pinned items automatically.",
        "- The CLI will binary-search ranked optional evidence and skills until the resume fits one page with no width overflow.",
        "",
        "## Job Description",
        "",
        job_text.strip(),
        "",
        "## Courses",
        "",
    ]
    for course in profile.courses:
        lines.append(f"- `{course.id}`: {course.title} ({course.pos})")

    lines.extend(["", "## Projects", ""])
    for project in profile.projects:
        lines.append(f"### `{project.id}` - {project.title} ({project.pos})")
        if project.tech:
            lines.append(f"- Tech: {', '.join(project.tech)}")
        if project.url:
            lines.append(f"- URL: {project.url}")
        for bullet in project.bullets:
            lines.append(f"- Bullet: {bullet}")
        lines.append("")

    lines.extend(["## Research", ""])
    for item in profile.research:
        lines.append(f"### `{item.id}` - {item.title} ({item.pos})")
        if item.venue:
            lines.append(f"- Venue: {item.venue}")
        if item.authors:
            lines.append(f"- Authors: {item.authors}")
        if item.abstract:
            lines.append(f"- Abstract: {item.abstract}")
        if item.url:
            lines.append(f"- URL: {item.url}")
        lines.append("")

    lines.extend(["## Skills", ""])
    for skill in profile.skills:
        category = skill.category or skill.title
        lines.append(f"### {category}")
        for item in skill.items:
            lines.append(f"- {item} ({skill.item_positions.get(item, 'pin')})")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
