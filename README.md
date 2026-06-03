# Resume Tailor

Local CLI that builds a one-page Jake-style resume from a YAML inventory and a job description.

```bash
rt validate --profile examples/profile.yaml
rt rank --profile examples/profile.yaml --job examples/job.md
rt generate --profile examples/profile.yaml --job examples/job.md --out out/acme-backend
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

- `KevinJinResume.tex`
- `KevinJinResume.pdf`

The CLI never rewrites resume bullets. Final resume text comes from the YAML inventory and bundled template snippets.

## Placement DSL

Each selectable item can define `pos`:

- `opt`: optional, ranked, reorderable, prunable. This is the default.
- `req`: required, ranked/reorderable, never pruned.
- `pin`: pinned, always included, keeps YAML position, never pruned.

## LaTeX

The generator uses `latexmk` when available, then falls back to `pdflatex`.
