from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import re
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape

from resume_tailor.assemble import ResumeSelection
from resume_tailor.models import Profile
from resume_tailor.text import latex_escape

OUTPUT_BASENAME = "Resume"


def render_resume(
    profile: Profile,
    selection: ResumeSelection,
    output_dir: Path,
    template_path: Path | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    env = _environment(template_path)
    template = env.get_template(template_path.name if template_path else "jakes_resume.tex.j2")
    tex = template.render(
        profile=profile,
        selection=selection,
        forgejo_note=forgejo_note(profile, selection),
    )
    tex_path = output_dir / f"{OUTPUT_BASENAME}.tex"
    tex_path.write_text(tex, encoding="utf-8")
    return tex_path


def _environment(template_path: Path | None) -> Environment:
    if template_path:
        loader = FileSystemLoader(str(template_path.parent))
    else:
        loader = PackageLoader("resume_tailor", "templates")
    env = Environment(
        loader=loader,
        autoescape=select_autoescape(default_for_string=False, enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["latex"] = latex_escape
    env.filters["bold_author"] = bold_author_name
    return env


def forgejo_note(profile: Profile, selection: ResumeSelection) -> str | None:
    if not profile.forgejo.code or not profile.forgejo.host:
        return None
    selected_urls: list[str] = []
    for item in [*selection.projects, *selection.research]:
        selected_urls.extend(item.all_urls())
    if not any(_url_matches_host(url, profile.forgejo.host) for url in selected_urls):
        return None
    return profile.forgejo.note_template.replace("{code}", profile.forgejo.code)


def bold_author_name(authors: str | None, name: str) -> str:
    escaped_authors = latex_escape(authors)
    escaped_name = latex_escape(name)
    if not escaped_authors or not escaped_name:
        return escaped_authors
    pattern = re.escape(escaped_name) + r"\*?"
    return re.sub(pattern, lambda match: rf"\textbf{{{match.group(0)}}}", escaped_authors, count=1)


def _url_matches_host(url: str, host: str) -> bool:
    parsed = urlparse(url)
    hostname = parsed.hostname or urlparse(f"https://{url}").hostname or ""
    return hostname == host or hostname.endswith(f".{host}")
