# Resume Tailor

Local CLI that builds a one-page Jake-style resume from a YAML inventory and a job description.

```bash
rt validate --profile examples/profile.yaml
rt rank --profile examples/profile.yaml --job examples/job.md
rt generate --profile examples/profile.yaml --job examples/job.md --out out/acme-backend
rt selection-prompt --profile examples/profile.yaml --job examples/job.md --out out/acme-selection-prompt.md
rt generate-ranked --profile examples/profile.yaml --ranking examples/rankings/acme.yaml --out out/acme-backend
rt render-selection --profile examples/profile.yaml --selection examples/selections/oracle-oci-network-load-balancer.yaml --out out/oracle-oci-network-load-balancer
```

## Nix + direnv

```bash
direnv allow
rt validate --profile examples/profile.yaml
rt generate --profile examples/profile.yaml --job examples/job.md --out out/acme-backend
```

The flake provides Python dependencies, the `rt`/`resume-tailor` commands, and a LaTeX toolchain. Model and embedding caches are kept under `.cache/` while the direnv environment is active.
The Python dependencies are installed into direnv's project-local virtualenv from `pyproject.toml`.

`generate` writes:

- `Resume.tex`
- `Resume.pdf`

The CLI never rewrites resume bullets. Final resume text comes from the YAML inventory and bundled template snippets.

## Selection DSL

Selectable sections use bracket groups:

```yaml
courses:
  select: "Distributed Systems, Cloud Computing, [Compilers | Computer Networks]"

projects:
  select: "[social_discovery_frontend | metadata_private_write_database | db_query_optimizer | minijava_compiler]"
  items:
    - id: social_discovery_frontend
      title: Social Discovery Platform Frontend

research:
  select: "[prompt_language_leakage | java_resource_leak_repair]"

skills:
  - title: Languages
    items: "Python, Java, C/C++, [JavaScript | Go | Swift], HTML, CSS, SQL"
```

The same bracket-and-pipe syntax is used across the YAML, but each section applies it differently:

- Courses: items outside brackets are included first; bracketed items are ranked against the job description and added while the course line stays within `course_line_max_chars`.
- Projects: `projects.select` defines the ranked project candidate pool. Projects are not pinned, even when a project id appears outside brackets.
- Research: `research.select` uses the same bracket syntax. Bracketed research entries are ranked and compete with projects during the layout pruning loop.
- Skills: items outside brackets are pinned. Bracketed items are optional; the generator tries to add them in YAML order and keeps each one only if the resume still fits.

`generate` keeps a closed layout loop: it compiles the LaTeX, requires a one-page PDF, and rejects LaTeX logs with overfull `\hbox` warnings. If the resume does not fit, it first drops the lowest-ranked optional project or research item, then drops the weakest keyword-match project or research item as a last resort. Optional skills are tested independently from project, research, and course ranking.

## Explicit Selections

Use `selection-prompt` before skill-based selection. It writes a prompt-friendly inventory containing the job description, all course options, every project, every research item, and all skill items:

```bash
rt selection-prompt --profile examples/profile.yaml --job examples/job.md --out out/acme-selection-prompt.md
```

The LLM should return a complete ranking of every optional value:

```yaml
evidence:
  - metadata_private_write_database
  - java_resource_leak_repair
  - discord_server_configurator

courses:
  - Cloud Computing
  - Database Systems

skills:
  Languages:
    - JavaScript
    - Go
  Frameworks & Databases:
    - React
    - FastAPI
```

`generate-ranked` validates that every optional project, research item, course, and skill item appears exactly once in the ranking YAML. The CLI keeps pinned profile items automatically, uses the ranking order for optional inclusion, and binary-searches optional evidence and skills until the compiled PDF is one page with no overfull `\hbox` warnings. Skill rankings decide which optional skills are included; the profile DSL still controls display position, so `skill1, [skill2], skill3, [skill4]` renders selected optional skills in those bracket locations.

```bash
rt generate-ranked --profile examples/profile.yaml --ranking examples/rankings/acme.yaml --out out/acme
```

Use `render-selection` only when project, research, course, and skill choices are already decided outside the profile ranking rules:

```yaml
courses:
  - Distributed Systems
  - Computer Networks

projects:
  - reliable_data_transfer_protocol
  - metadata_private_write_database

research:
  - prompt_language_leakage

skills:
  - category: Languages
    items:
      - Python
      - Java
      - C/C++
      - Go
```

`render-selection` maps project and research IDs through the profile, renders the LaTeX once, compiles the PDF, and reports page count plus overfull `\hbox` status. Pinned projects and research from the profile are always included even if omitted from the explicit selection file. By default it exits with code 2 when the result is more than one page or has overfull boxes; pass `--allow-overflow` for format inspection drafts.

## LaTeX

The generator uses `latexmk` when available, then falls back to `pdflatex`.
