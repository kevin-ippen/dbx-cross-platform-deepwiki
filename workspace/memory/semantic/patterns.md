# Patterns & Conventions

> How we do things here. Agents should follow these unless there's a documented reason to deviate.
> Promote project-specific patterns here when they appear in 2+ projects.

## Naming

- **Tables:** `{domain}_{entity}` or medallion `{layer}_{entity}` (e.g., `bronze_events`, `gold_scores`)
- **Schemas:** `{project}_{layer}` or domain-scoped (e.g., `myproject_bronze`, `myproject_silver`)
- **Jobs:** descriptive bundle resource names (`pipeline_ingest.yml`, `model_retrain.yml`)
- **Apps:** kebab-case (`my-app`, `data-explorer`)
- **Endpoints:** kebab-case (`my-model-v1`, `embedding-endpoint`)
- **Databricks CLI Profiles:** descriptive hyphenated (`prod-workspace`, `dev-workspace`)

## Project Structure

```
my-project/
  notebooks/        ← numbered pipeline stages (01_ingest.py, 02_transform.py)
  src/              ← reusable modules
  resources/        ← DAB YAML definitions
  config/           ← app-specific YAML
  tests/            ← test_{module}.py
  docs/             ← design specs
  databricks.yml    ← DAB root config
```

## Compute Selection

| Workload | Use |
|----------|-----|
| SQL queries | Serverless SQL Warehouse |
| Spark ETL notebooks | Serverless (`client: "1"`) |
| GPU / ML training | Single-node GPU cluster |
| Online inference | Model Serving endpoint |
| Natural language queries | Genie rooms |

## Auth Pattern (CRITICAL)

```bash
# ALWAYS clear env vars before any Databricks CLI command targeting a specific profile
env -u DATABRICKS_HOST -u DATABRICKS_TOKEN -u DATABRICKS_CONFIG_PROFILE \
  databricks [command] --profile [profile_name]
```

Shell env vars silently override `--profile` — this is the #1 source of "wrong workspace" bugs.

## Serverless Constraints (`client: "1"`)

- NO `torch`, `mlflow`, or third-party SDKs that don't support serverless — use raw HTTP + FMAPI
- NO `cache()` / `persist()` — use temp views or recompute
- NO `DEFAULT` in `CREATE TABLE`
- ALWAYS use explicit `StructType` schema with `createDataFrame()`
- `%pip install` + `restartPython()` MUST be the first cell
- `# COMMAND ----------` splits cells — if/else blocks CANNOT span cells

## Agent Architecture

- **No orchestration framework** — hand-rolled loops give full control and easier debugging
- **Deterministic retrieval** — bundle assembly via direct tool calls, NOT LLM reasoning
- **LLM only for generation** — drafting, summarization, scoring (not routing or retrieval)
- **Subagent pattern:** send a slice of context → get structured output → director integrates
- **Model routing:** cheap model = research/skimming, capable model = writing/complex reasoning

## Data Architecture

- **UC Volumes only:** `/Volumes/{catalog}/{schema}/{volume}/` — never `dbfs:/` or `/mnt/`
- **Medallion layers:** bronze (raw), silver (cleaned/joined), gold (business-ready)
- **Write pattern:** prefer temp view + `INSERT INTO` over `saveAsTable` with append mode (avoids partition inference issues on Spark Connect)

## Deployment

- **DABs** for all Databricks resources (notebooks, jobs, apps) — `databricks bundle deploy/run`
- **`bundle deploy --var`** MUST precede `bundle run` to rebake job base_parameters
- **`bundle validate`** before every production deploy
- **Never push directly to `main`** without a feature branch + review

---

*Last updated: [fill in date when you first populate this for your workspace]*
