from __future__ import annotations

from pathlib import Path

import typer

from resume_tailor.assemble import (
    ResumeSelection,
    lowest_ranked_evidence_id,
    lowest_ranked_optional_id,
    select_resume,
    select_skills,
)
from resume_tailor.io import ProfileLoadError, load_job, load_profile
from resume_tailor.latex import LatexError, compile_pdf, has_overfull_hbox, page_count
from resume_tailor.models import Position, Profile, skill_candidates, slugify
from resume_tailor.ranking import DEFAULT_MODEL, CachedEmbedder, SentenceTransformerEmbedder, rank_items
from resume_tailor.ranked_selection import (
    RankedCandidatePool,
    RankedSelectionLoadError,
    build_ranked_resume_selection,
    load_ranked_selection,
    validate_ranked_selection,
)
from resume_tailor.render import OUTPUT_BASENAME, render_resume
from resume_tailor.selection import SelectionLoadError, build_resume_selection, load_explicit_selection
from resume_tailor.selection_prompt import build_selection_prompt

app = typer.Typer(no_args_is_help=True)


@app.command()
def validate(profile: Path = typer.Option(..., "--profile", "-p")) -> None:
    """Validate a resume inventory YAML file."""
    try:
        loaded = load_profile(profile)
    except ProfileLoadError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(
        "Valid profile: "
        f"{len(loaded.experience)} experience, "
        f"{len(loaded.projects)} projects, "
        f"{len(loaded.research)} research, "
        f"{len(loaded.courses)} courses"
    )


@app.command()
def rank(
    profile: Path = typer.Option(..., "--profile", "-p"),
    job: Path = typer.Option(..., "--job", "-j"),
    model: str = typer.Option(DEFAULT_MODEL, "--model"),
) -> None:
    """Print ranking tables for the job description."""
    loaded = _load_profile_or_exit(profile)
    job_text = _load_job_or_exit(job)
    embedder = CachedEmbedder(SentenceTransformerEmbedder(model))
    rankings = _rank_all(loaded, job_text, embedder)
    for label, ranked in rankings.items():
        typer.echo(f"\n{label}:")
        if not ranked:
            typer.echo("  (none)")
        for rank_index, ranked_item in enumerate(ranked, start=1):
            typer.echo(
                f"  {rank_index:>2}. {ranked_item.item.id} "
                f"score={ranked_item.score:.3f} "
                f"semantic={ranked_item.semantic_score:.3f} "
                f"keyword={ranked_item.keyword_score:.3f}"
            )


@app.command()
def generate(
    profile: Path = typer.Option(..., "--profile", "-p"),
    job: Path = typer.Option(..., "--job", "-j"),
    out: Path = typer.Option(..., "--out", "-o"),
    template: Path | None = typer.Option(None, "--template"),
    model: str = typer.Option(DEFAULT_MODEL, "--model"),
) -> None:
    """Generate Resume.tex and Resume.pdf."""
    loaded = _load_profile_or_exit(profile)
    job_text = _load_job_or_exit(job)
    embedder = CachedEmbedder(SentenceTransformerEmbedder(model))
    rankings = _rank_all(loaded, job_text, embedder)
    selection = select_resume(
        loaded,
        rankings["courses"],
        rankings["projects"],
        rankings["research"],
        rankings["skill_items"],
    )

    try:
        selection = _compile_until_one_page(loaded, selection, rankings, out, template)
    except LatexError as exc:
        raise typer.Exit(_error(f"LaTeX failed: {exc}")) from exc

    _print_summary(selection, rankings)
    if selection.needs_review:
        raise typer.Exit(code=2)


@app.command("render-selection")
def render_selection_command(
    profile: Path = typer.Option(..., "--profile", "-p"),
    selection: Path = typer.Option(..., "--selection", "-s"),
    out: Path = typer.Option(..., "--out", "-o"),
    template: Path | None = typer.Option(None, "--template"),
    require_one_page: bool = typer.Option(True, "--require-one-page/--allow-overflow"),
) -> None:
    """Render an explicit selection YAML without running ranking."""
    loaded = _load_profile_or_exit(profile)
    try:
        explicit = load_explicit_selection(selection)
        resume_selection = build_resume_selection(loaded, explicit)
    except SelectionLoadError as exc:
        raise typer.Exit(_error(str(exc))) from exc

    try:
        tex_path = render_resume(loaded, resume_selection, out, template)
        pdf_path = compile_pdf(tex_path)
    except LatexError as exc:
        raise typer.Exit(_error(f"LaTeX failed: {exc}")) from exc

    pages = page_count(pdf_path)
    overfull = has_overfull_hbox(tex_path)
    _print_summary(resume_selection)
    typer.echo(f"PDF: {pdf_path.resolve()}")
    typer.echo(f"Pages: {pages}")
    typer.echo(f"Overfull hbox: {overfull}")
    if require_one_page and (pages > 1 or overfull):
        raise typer.Exit(code=2)


@app.command("selection-prompt")
def selection_prompt_command(
    profile: Path = typer.Option(..., "--profile", "-p"),
    job: Path = typer.Option(..., "--job", "-j"),
    out: Path | None = typer.Option(None, "--out", "-o"),
) -> None:
    """Write a prompt-friendly inventory for skill/manual selection."""
    loaded = _load_profile_or_exit(profile)
    job_text = _load_job_or_exit(job)
    prompt = build_selection_prompt(loaded, job_text)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(prompt, encoding="utf-8")
        typer.echo(f"Selection prompt: {out.resolve()}")
    else:
        typer.echo(prompt)


@app.command("generate-ranked")
def generate_ranked_command(
    profile: Path = typer.Option(..., "--profile", "-p"),
    ranking: Path = typer.Option(..., "--ranking", "-r"),
    out: Path = typer.Option(..., "--out", "-o"),
    template: Path | None = typer.Option(None, "--template"),
) -> None:
    """Generate a resume from a complete LLM ranking YAML."""
    loaded = _load_profile_or_exit(profile)
    try:
        ranked = load_ranked_selection(ranking)
        pool = validate_ranked_selection(loaded, ranked)
        selection = _compile_ranked_until_one_page(loaded, pool, out, template)
    except RankedSelectionLoadError as exc:
        raise typer.Exit(_error(str(exc))) from exc
    except LatexError as exc:
        raise typer.Exit(_error(f"LaTeX failed: {exc}")) from exc

    _print_summary(selection)
    pdf_path = out / f"{OUTPUT_BASENAME}.pdf"
    tex_path = out / f"{OUTPUT_BASENAME}.tex"
    if pdf_path.exists():
        typer.echo(f"PDF: {pdf_path.resolve()}")
        typer.echo(f"Pages: {page_count(pdf_path)}")
        typer.echo(f"Overfull hbox: {has_overfull_hbox(tex_path)}")
    if selection.needs_review:
        raise typer.Exit(code=2)


def _compile_until_one_page(
    profile: Profile,
    selection: ResumeSelection,
    rankings: dict[str, list],
    out: Path,
    template: Path | None,
) -> ResumeSelection:
    max_attempts = profile.layout.max_compile_attempts
    allowed_skill_ids: set[str] = set()
    testing_skill: tuple[str, str, str] | None = None
    optional_skill_queue = _optional_skill_queue(profile)
    skill_index = 0
    for attempt in range(1, max_attempts + 1):
        selection.compile_attempts = attempt
        tex_path = render_resume(profile, selection, out, template)
        pdf_path = compile_pdf(tex_path)
        fits_page = page_count(pdf_path) <= 1
        fits_width = not has_overfull_hbox(tex_path)
        if fits_page and fits_width:
            testing_skill = None
            if skill_index < len(optional_skill_queue):
                next_skill = optional_skill_queue[skill_index]
                skill_index += 1
                allowed_skill_ids.add(next_skill[2])
                testing_skill = next_skill
                selection = selection.with_skills(
                    select_skills(profile, rankings["skill_items"], allowed_skill_ids=allowed_skill_ids)
                )
                continue
            return selection
        if testing_skill is not None:
            allowed_skill_ids.discard(testing_skill[2])
            selection = selection.with_skills(
                select_skills(profile, rankings["skill_items"], allowed_skill_ids=allowed_skill_ids)
            )
            testing_skill = None
            continue
        evidence_rankings = [*rankings["projects"], *rankings["research"]]
        prune_id = lowest_ranked_optional_id(selection, evidence_rankings)
        if prune_id is None:
            prune_id = lowest_ranked_evidence_id(selection, evidence_rankings)
        if prune_id is None:
            selection.needs_review = "required_or_pinned_content_exceeds_page_or_width"
            return selection
        selection = selection.without_item(prune_id)
    selection.needs_review = f"exceeded_max_compile_attempts_{max_attempts}"
    return selection


def _compile_ranked_until_one_page(
    profile: Profile,
    pool: RankedCandidatePool,
    out: Path,
    template: Path | None,
) -> ResumeSelection:
    attempts = 0

    def candidate(evidence_count: int, optional_skill_counts: dict[str, int] | None = None) -> ResumeSelection:
        return build_ranked_resume_selection(profile, pool, evidence_count, optional_skill_counts or {})

    def fits(selection: ResumeSelection) -> bool:
        nonlocal attempts
        attempts += 1
        selection.compile_attempts = attempts
        tex_path = render_resume(profile, selection, out, template)
        pdf_path = compile_pdf(tex_path)
        return page_count(pdf_path) <= 1 and not has_overfull_hbox(tex_path)

    evidence_count = _max_fitting_count(
        len(pool.evidence),
        lambda count: fits(candidate(count, {})),
    )
    base_selection = candidate(evidence_count, {})
    if not fits(base_selection):
        base_selection.compile_attempts = attempts
        base_selection.needs_review = "required_or_pinned_content_exceeds_page_or_width"
        return base_selection

    optional_skill_counts: dict[str, int] = {}
    for skill in profile.skills:
        category = skill.category or skill.title
        if category not in pool.skill_choices_by_category:
            continue
        optional_skill_counts[category] = _max_fitting_count(
            len(pool.skill_choices_by_category[category]),
            lambda count, category=category: fits(
                candidate(evidence_count, {**optional_skill_counts, category: count})
            ),
        )

    final_selection = candidate(evidence_count, optional_skill_counts)
    fits(final_selection)
    final_selection.compile_attempts = attempts
    return final_selection


def _max_fitting_count(max_count: int, fits_count) -> int:
    low = 0
    high = max_count
    best = 0
    while low <= high:
        mid = (low + high) // 2
        if fits_count(mid):
            best = mid
            low = mid + 1
        else:
            high = mid - 1
    return best


def _optional_skill_queue(profile: Profile) -> list[tuple[str, str, str]]:
    queue = []
    for skill in profile.skills:
        category = skill.category or skill.title
        for item in skill.items:
            if skill.item_positions.get(item, Position.PIN) == Position.OPT:
                queue.append((category, item, f"{slugify(category)}__{slugify(item)}"))
    return queue


def _rank_all(profile: Profile, job_text: str, embedder: CachedEmbedder) -> dict[str, list]:
    return {
        "courses": rank_items(job_text, profile.courses, embedder),
        "projects": rank_items(job_text, profile.projects, embedder),
        "research": rank_items(job_text, profile.research, embedder),
        "skill_items": rank_items(job_text, skill_candidates(profile), embedder),
    }


def _load_profile_or_exit(path: Path) -> Profile:
    try:
        return load_profile(path)
    except ProfileLoadError as exc:
        raise typer.Exit(_error(str(exc))) from exc


def _load_job_or_exit(path: Path) -> str:
    try:
        return load_job(path)
    except FileNotFoundError as exc:
        raise typer.Exit(_error(str(exc))) from exc


def _print_summary(selection: ResumeSelection, rankings: dict[str, list] | None = None) -> None:
    typer.echo("Selected projects: " + _ids(selection.projects))
    typer.echo("Selected research: " + _ids(selection.research))
    typer.echo("Selected courses: " + (", ".join(selection.courses) or "(none)"))
    if rankings is not None:
        course_fill_order = [rank.item.title for rank in rankings.get("courses", [])]
        typer.echo("Course fill order: " + (", ".join(course_fill_order) or "(none)"))
        research_fill_order = [rank.item.id for rank in rankings.get("research", [])]
        typer.echo("Research fill order: " + (", ".join(research_fill_order) or "(none)"))
    skill_lines = [f"{skill.category}: {', '.join(skill.items)}" for skill in selection.skills]
    typer.echo("Selected skills: " + ("; ".join(skill_lines) or "(none)"))
    typer.echo("Pruned optional IDs: " + (", ".join(selection.pruned_ids) or "(none)"))
    typer.echo(f"Compile attempts: {selection.compile_attempts}")
    for warning in selection.warnings:
        typer.echo(f"Warning: {warning}")
    if selection.needs_review:
        typer.echo(f"needs_review: {selection.needs_review}")


def _ids(items: list) -> str:
    return ", ".join(item.id for item in items) or "(none)"


def _error(message: str) -> int:
    typer.echo(message, err=True)
    return 1


if __name__ == "__main__":
    app()
