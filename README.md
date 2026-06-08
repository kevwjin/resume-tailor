# Resume Tailor

Local CLI that builds a one-page Jake-style resume from a YAML inventory and a job description.

The profile YAML is the source of truth: it stores contact information, education,
experience bullets, optional courses, optional projects, optional research, and skills.
The CLI ranks or accepts a ranking of that inventory, renders the selected content
through the bundled Jake-style LaTeX template, and checks that the compiled result is
one page with no overfull `\hbox` warnings.

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

## Output Files

All render commands write into the directory passed with `--out`.
For example:

```bash
rt generate-ranked --profile examples/profile.yaml --ranking examples/rankings/acme.yaml --out out/acme
```

writes:

- `out/acme/Resume.tex`
- `out/acme/Resume.pdf`
- LaTeX build files such as `Resume.log`, `Resume.aux`, and `Resume.fls`

`selection-prompt` writes a Markdown prompt inventory to the path passed with `--out`,
for example `out/acme-selection-prompt.md`.

The CLI never rewrites resume bullets. Final resume text comes from the YAML inventory and bundled template snippets.

## Selection Syntax

Selectable sections use comma-separated values, bracket groups, and pipe-separated
alternatives inside a bracket group:

```yaml
courses:
  select: "Machine Learning, Distributed Systems, [Cloud Computing | Database Systems]"
```

The same bracket-and-pipe syntax is used across the YAML, but each section applies
it differently:

- Courses: items outside brackets are pinned. Bracketed items are optional and must be ranked for `generate-ranked`.
- Projects: `projects.select` defines the ranked project candidate pool. Projects are not pinned, even when a project id appears outside brackets.
- Research: `research.select` uses the same bracket syntax. Bracketed research entries are ranked and compete with projects during the layout pruning loop.
- Skills: items outside brackets are pinned. Bracketed items are optional; the generator tries to add them in YAML order and keeps each one only if the resume still fits.

`generate` keeps a closed layout loop: it compiles the LaTeX, requires a one-page PDF, and rejects LaTeX logs with overfull `\hbox` warnings. If the resume does not fit, it first drops the lowest-ranked optional project or research item, then drops the weakest keyword-match project or research item as a last resort. Optional skills are tested independently from project, research, and course ranking.

`max_project_tech_items` is an optional rendering cap for project headings. It limits
how many technologies from each project's `tech` list appear next to the title. It
does not affect ranking or project selection.

## Complete Profile Example

This is a complete anonymized profile YAML. YAML key order is not semantically
important, but the example keeps selection-capable sections easy to scan and puts
skills before education, research, experience, and projects.

```yaml
courses:
  select: "Machine Learning, Distributed Systems, [Cloud Computing | Database Systems | Information Security | Compilers | Computer Networks | Linear Algebra | Graph Theory | Real Analysis]"

skills:
  - id: languages
    title: Languages
    items: "Python, Java, C/C++, [JavaScript | Go | CUDA | Bash | Verilog | Swift], HTML, CSS, SQL"
    tags: [programming languages]
  - id: frameworks_databases
    title: Frameworks & Databases
    items: "React, [FastAPI | Express.js | PostgreSQL | MongoDB | SwiftUI], Jupyter Notebook"
    tags: [web frameworks, databases]
  - id: cloud_developer_tools
    title: Cloud & Developer Tools
    items: "Codex, AWS, Terraform, Nix, Git, [Perforce]"
    tags: [cloud, infrastructure, developer tools]

education:
  - id: state_ms_cs
    school: State University
    degree: "Master of Science in Computer Science, GPA: 3.90/4.00"
    location: City, ST
    dates: (Expected) Dec. 2026
    details:
      - Teaching assistant for systems programming
  - id: public_bs_cs
    school: Public University
    degree: Bachelor of Science in Computer Science
    location: City, ST
    dates: June 2024

research:
  select: "llm_generated_data_leakage, [llm_static_analysis_repair]"
  items:
    - id: llm_generated_data_leakage
      title: Leakage Signals in LLM-Generated Data
      url: https://example.com/papers/llm-generated-data-leakage.pdf
      venue: 2026 Workshop Paper
      authors: Example Candidate, Collaborator Name
      abstract: Study of whether downstream sequence models inherit latent signatures from LLM-generated data under controlled generation settings.
      tags: [machine learning, llm, sequence models, research]
      rank_text: Empirical ML research on LLM outputs, downstream model behavior, and controlled experiments.
    - id: llm_static_analysis_repair
      title: LLM Harness for Static Analysis Repairs
      url: https://example.com/papers/llm-static-analysis-repair.pdf
      venue: 2025 Preprint
      authors: Example Candidate*, Anonymous Collaborator*
      abstract: Evaluation of whether LLMs can repair resource-management bugs that static analysis tools struggle to handle.
      tags: [llm, static analysis, software engineering, research]
      rank_text: Applied LLM tooling research for software reliability, evaluation harnesses, and program repair.

experience:
  - id: network_platform_intern
    company: Network Platform Company
    title: Software Engineer Intern | Python, C++, Linux
    location: City, ST
    dates: June 2025 -- Sept. 2025
    bullets:
      - Built a CLI tool used by engineers to query generated hardware configuration data
      - Optimized repeated configuration calls in a hardware-test workflow for internal users
      - Created a reusable parser library from YAML source data consumed at build time
  - id: routing_systems_intern
    company: Cloud Networking Company
    title: Software Engineer Intern | Python, C++, Distributed Systems
    location: City, ST
    dates: June 2024 -- Sept. 2024
    bullets:
      - Implemented protocol support for routing metadata exchanged between network services
      - Added validation that rejects invalid router commands before they reach production systems
      - Improved connectivity tracking by integrating failure-detection signals into an internal workflow

projects:
  select: "[metadata_private_write_database | compiler_backend | search_sat_solver | gpu_model_acceleration | fullstack_dashboard | reliable_transport_protocol]"
  items:
    - id: metadata_private_write_database
      title: Distributed Metadata-Private Write Database
      url: https://github.com/example-candidate/private-db
      links:
        - label: docs
          url: https://example.com/private-db-docs
      tech: [Go, Terraform, AWS, Distributed Systems]
      bullets:
        - Designed a distributed architecture for metadata-private writes with coordinator-based routing and durable control state
        - Benchmarked horizontal write scaling across active shards with near-linear throughput improvement
      tags: [distributed systems, privacy, cloud]
      rank_text: Privacy-preserving distributed database with AWS-backed ingestion, failover, and scaling experiments.
    - id: compiler_backend
      title: Compiler Backend
      url: https://git.example.com/example/compiler
      tech: [Java, RISC-V, Compilers]
      bullets:
        - Built semantic checking, IR lowering, register allocation, and RISC-V code generation for a small object-oriented language
        - Improved generated-code execution speed using liveness analysis and linear-scan register allocation
      tags: [compilers, programming languages, systems]
    - id: search_sat_solver
      title: Search and SAT Encodings
      url: https://git.example.com/example/search-sat
      tech: [Python, A* Search, SAT]
      bullets:
        - Implemented a search solver with domain heuristics for state-space planning problems
        - Encoded graph coloring as SAT by generating CNF clauses for assignments and constraints
      tags: [artificial intelligence, search, formal methods]
    - id: gpu_model_acceleration
      title: GPU Model Acceleration
      url: https://git.example.com/example/gpu-model-acceleration
      tech: [CUDA, C/C++, GPU, Machine Learning]
      bullets:
        - Mapped neural-network inference stages onto GPU execution paths for high-throughput evaluation
        - Compared accelerated execution against sequential baselines using generated benchmark inputs
      tags: [machine learning, performance, gpu]
    - id: fullstack_dashboard
      title: Full-stack Operations Dashboard
      url: https://github.com/example-candidate/dashboard
      tech: [React, FastAPI, PostgreSQL, REST APIs]
      bullets:
        - Built authenticated workflows for importing, editing, and exporting reusable configuration templates
        - Modeled application configuration as a schema with validation and inherited permissions
      tags: [full stack, api, database]
    - id: reliable_transport_protocol
      title: Reliable Transport Protocol
      url: https://git.example.com/example/reliable-transport
      tech: [C++, UDP, BSD Sockets, Networking]
      bullets:
        - Implemented a reliable transport protocol over UDP with sequencing, cumulative acknowledgments, retransmission, and teardown
        - Transferred large files reliably under simulated packet loss using fixed-size payloads
      tags: [networking, c++, systems]

personal:
  name: Example Candidate
  email: candidate@example.com
  phone: 555-555-5555
  citizenship: US Citizen
  website: example.com/cv
  website_label: example.com
  linkedin: linkedin.com/in/example-candidate
  github: github.com/example-candidate
  links:
    - label: portfolio
      url: example.com/projects

forgejo:
  host: git.example.com
  code: demo2026
  note_template: "\\faExclamationCircle\\hspace{0.5em}Enter code \\textbf{{code}} to access close-sourced repositories"

layout:
  max_project_tech_items: 6
  max_compile_attempts: 50
```

## Using The Skill

For Codex-assisted tailoring, use the bundled `software-resume-tailor` skill as the
ranking authority and the CLI as the deterministic renderer.

1. Save the job description as Markdown, for example `examples/jobs/acme.md`.
2. Generate the complete inventory prompt:

   ```bash
   rt selection-prompt --profile examples/profile.yaml --job examples/jobs/acme.md --out out/acme-selection-prompt.md
   ```

3. Ask Codex to use `software-resume-tailor` on that prompt or paste the job
   description with `[$software-resume-tailor](/home/kevwjin/.codex/skills/software-resume-tailor/SKILL.md)`.
4. Write the complete ranking YAML under `examples/rankings/acme.yaml`.
5. Render the resume:

   ```bash
   rt generate-ranked --profile examples/profile.yaml --ranking examples/rankings/acme.yaml --out out/acme
   ```

The skill must rank every optional project, research item, course, and skill item
exactly once. The CLI then includes pinned profile items automatically and searches
for the largest one-page resume with no overfull `\hbox` warnings.

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

`generate-ranked` validates that every optional project, research item, course, and skill item appears exactly once in the ranking YAML. The CLI keeps pinned profile items automatically, uses the ranking order for optional inclusion, and binary-searches optional evidence, courses, and skills until the compiled PDF is one page with no overfull `\hbox` warnings. Skill rankings decide which optional skills are included; the profile DSL still controls display position, so `skill1, [skill2], skill3, [skill4]` renders selected optional skills in those bracket locations.

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
