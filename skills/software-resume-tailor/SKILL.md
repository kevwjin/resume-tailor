---
name: software-resume-tailor
description: Use when tailoring a software engineering resume to a job description, especially when ranking projects, skills, courses, research, or resume inventory for backend, frontend, full-stack, ML/AI, systems, infrastructure, mobile, security, crypto/privacy, or general SWE roles. Prefer this skill when local embeddings or keyword scores may miss recruiter-style relevance.
---

# Software Resume Tailor

## Purpose

Use recruiter-style software engineering judgment to rank resume inventory against a job description. Preserve existing resume wording unless the user asks for edits.

The main output is an ordered recommendation: which projects, skills, courses, and research should appear for this role, with short rationale and any surprising tradeoffs.

## Workflow

1. Read the job description for role type, required skills, preferred skills, domain, seniority, and repeated signals.
2. Generate and read the complete selection inventory with `rt selection-prompt --profile examples/profile.yaml --job <job.md> --out <prompt.md>` so every available project, research item, course, and skill item is visible before choosing.
3. Rank skills and courses independently. Rank projects and research first within their own pools, then compare the strongest project and research items as one shared evidence budget when space is tight.
4. Explain surprising choices before changing files.
5. Treat this skill's judgment as the ranking source of truth. Do not blend it with local embedding or keyword rankings.
6. Write a complete ranking YAML containing every optional evidence item, optional course, and optional skill item exactly once, then call `rt generate-ranked --profile examples/profile.yaml --ranking <ranking.yaml> --out <out-dir>`. Let the CLI include pinned profile items and binary-search optional content until the resume compiles to one page with no overfull hbox. For skills, the ranking controls inclusion priority; the profile DSL controls final display position.

## Ranking Signals

Weight explicit job requirements more than vague semantic similarity. Repeated or concrete terms in the job description matter most.

Prefer:
- demonstrated ownership over toy examples
- peer-reviewed, accepted, or publication-style research when it demonstrates technical depth, experimental rigor, ML/AI relevance, systems reasoning, or credibility beyond a project
- production, deployment, reliability, testing, monitoring, or performance work
- project domain alignment with the job's actual responsibilities
- technologies the candidate is comfortable defending in an interview
- breadth only when the job is broad

Deprioritize:
- projects that match only on generic words like "science", "modeling", "tool", or "system"
- research that is only loosely related to the role when stronger hands-on project evidence exists
- coursework-only relevance when stronger project evidence exists
- impressive but off-domain projects unless the job values that domain
- long skill lists that overflow or dilute stronger signals

## Role Heuristics

Backend / infrastructure:
Prioritize distributed systems, databases, networking, APIs, cloud, queues, observability, reliability, scaling, and production services.

ML / AI / data:
Prioritize Python systems, ML pipelines, model deployment, evaluation, data processing, high-performance compute, experiments, and research with measurable engineering.

Full stack:
Prioritize React or frontend framework work, APIs, auth, databases, user workflows, product polish, and end-to-end ownership.

Frontend / mobile:
Prioritize UI state, interaction design, platform-native work, performance, accessibility, design systems, and product-facing implementation.

Systems / performance:
Prioritize C/C++, CUDA, FPGA, networking, compilers, OS-adjacent work, profiling, low-level performance, and hardware-aware engineering.

Programming languages / compilers:
Prioritize interpreters, compilers, type checking, scoping, IR, register allocation, codegen, parsing, and language semantics.

Security / crypto / privacy:
Prioritize cryptographic protocols, privacy-preserving systems, metadata privacy, authentication, authorization, access control, threat modeling, information security, and secure infrastructure.

Cloud / DevOps:
Prioritize AWS/GCP/Azure, Terraform, CI/CD, containers, queues, storage, databases, deployment, monitoring, failover, and operational reliability.

General SWE:
Prioritize clear engineering ownership, debugging, maintainability, tests, collaboration, product impact, APIs, data models, and shipping complete features.

## Judgment Rules

When ranking skills, preserve the user's confidence order unless the job has a strong reason to include or exclude an optional skill. Do not let project ranking determine skills; evaluate skills independently.

When ranking courses, prefer job-relevant courses but keep the list short enough to preserve project space.

Treat research as optional evidence unless the user says otherwise. Include it when peer-reviewed or publication-style work adds trust, depth, or domain match beyond the next project; omit it when projects provide stronger hands-on evidence for the role. Compare optional research directly against optional projects as one evidence pool when deciding what should survive the space budget.

For research residencies, ML residencies, applied scientist roles, PhD/Master's research internships, or roles that emphasize experiments, publications, modeling, or scientific communication, strongly prefer including at least one credible research item. In those cases, research should usually survive over a weaker or only loosely related project.

For AI-focused tooling companies or AI-focused companies in general, strongly prefer including the LLM resource-leak repair research. Treat it as applied LLM tooling evidence because it uses LLMs to automate Java resource-leak repair, not as theory-only research.

When in doubt, produce a proposed order and ask for discussion before editing the resume inventory.

## Output Shape

For discussion, use:

```text
Recommended projects:
1. project_id - reason
2. project_id - reason

Would deprioritize:
- project_id - reason
```

For implementation:

1. Provide exact IDs to force or prioritize.
2. Generate a complete inventory prompt with `rt selection-prompt --profile examples/profile.yaml --job <job.md> --out <prompt.md>`.
3. Validate the profile with the local CLI, for example `python -m resume_tailor.cli validate -p examples/profile.yaml`.
4. Write a complete ranking YAML:
   - `evidence`: every optional project and research id exactly once
   - `courses`: every optional course exactly once
   - `skills`: every optional skill item exactly once under its category
5. Render/compile the selected resume with `rt generate-ranked --profile examples/profile.yaml --ranking <ranking.yaml> --out <out-dir>`.
6. Report the output PDF path, selected IDs, page count, and overfull hbox status.
