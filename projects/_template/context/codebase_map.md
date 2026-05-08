# Codebase Map

> High-level map of what lives where. Agent reads this when touching code structure.
> Populated during bootstrap (see BOOTSTRAP.md Prompt 2).

## Repository / Workspace Layout

```
project-root/
  notebooks/        ← numbered pipeline stages
  src/              ← reusable modules
  resources/        ← DAB YAML resource definitions
  config/           ← app/job configuration
  tests/            ← test suite
  databricks.yml    ← DAB bundle root
  .deepwiki/        ← this memory system
```

*(Replace with your actual layout after bootstrap.)*

## Key Files

| File | Purpose | Tables / Resources It Touches |
|------|---------|-------------------------------|
| *(e.g. notebooks/01_ingest.py)* | *(raw ingest from source)* | *(bronze.events_raw)* |

## Where Things Run

| File | Runs On | Trigger |
|------|---------|---------|
| *(e.g. notebooks/01_ingest.py)* | *(Databricks Workflow Job 12345)* | *(Daily 2am UTC)* |

## Code Scattered Elsewhere

*(Notebooks or scripts outside the main project structure — the stuff that "shouldn't exist" but does.)*

| Location | What It Does | Status |
|----------|-------------|--------|
| *(path)* | *(purpose)* | *(keep / migrate / delete)* |

---

*Populated during bootstrap. Update when files are added, moved, or deleted.*
