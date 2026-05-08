# Schema State

> Current state of all tables, views, and models owned by this project.
> Agent-compiled from changelog.md. Update immediately when schemas change.

## Format

```
### {catalog}.{schema}.{table}
- **Status:** active | deprecated | pending-creation
- **Purpose:** one-line description
- **Key Columns:**
  - `col_name` (TYPE) — description
- **Write Pattern:** overwrite | append | MERGE on {key_col}
- **Upstream:** where the data comes from
- **Downstream:** what reads this table
- **Last Modified:** YYYY-MM-DD
```

---

## Tables

*(empty — populate from your first changelog entries)*

## Models / Endpoints

*(add registered models and serving endpoint details here)*

---

*Compiled from changelog entries. If you find a discrepancy, the changelog is authoritative — update this file and note it.*
