# Project Index

> One-line summary of each project + where its memory lives.
> Update this file when you add or retire a project.

## Active Projects

| Project | Description | Workspace | Catalog / Schema | Status |
|---------|-------------|-----------|------------------|--------|
| `my-first-project` | *(replace with your project description)* | `{your-workspace}` | `{catalog}.{schema}` | Active |

<!-- Add a row for each project you run:
| `project-slug` | Short description of what it does | `workspace-profile-name` | `catalog.schema` | Active/Paused/Archived |
-->

## Memory Paths

Each project's memory lives at:
```
projects/{project-slug}/
  NORTH_STAR.md               ← the why
  planning/goals.md           ← current priorities
  planning/phases.md          ← execution order
  planning/decisions.md       ← architectural choices
  planning/open_questions.md  ← blockers and cross-project deps
  memory/changelog.md         ← append-only session log
  memory/semantic/schemas.md  ← current schema state
  memory/semantic/gotchas.md  ← project-specific pitfalls
```

## Shared Assets (Workspace Level)

Tables, endpoints, or libraries used by multiple projects. Details in `context/cross_references.md`.

| Asset | Type | Owner Project | Consumers |
|-------|------|--------------|-----------|
| *(shared table name)* | Delta table | *(owner)* | *(consumer A, consumer B)* |

## Archived Projects

| Project | Archived Date | Reason |
|---------|--------------|--------|
| *(none yet)* | — | — |
