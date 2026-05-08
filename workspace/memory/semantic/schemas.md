# Workspace-Level Schemas

> Tables and views that are SHARED across multiple projects.
> Project-specific schemas live in `projects/{name}/memory/semantic/schemas.md`.
> Promote a schema entry here once it is consumed by more than one project.

## Format

Each entry:
```
### {catalog}.{schema}.{table_or_view}
- **Status:** active | deprecated | pending
- **Purpose:** one line
- **Key Columns:** col (type) — description, ...
- **Owner Project:** which project writes it
- **Consumers:** which other projects read it
- **Last Modified:** YYYY-MM-DD
```

---

## Shared Tables

*(empty — add entries when a table is consumed by more than one project)*

---

*Detailed per-project schemas live in `projects/{project-name}/memory/semantic/schemas.md`.*
