# Gotchas & Anti-Patterns

> Platform-general lessons. Format: **What happened → Why → What to do instead.**
> Promote project-specific gotchas here once they appear in 2+ projects.

## Databricks CLI / Auth

- **Shell env vars override `--profile`** → `DATABRICKS_HOST` / `DATABRICKS_TOKEN` / `DATABRICKS_CONFIG_PROFILE` in the shell silently override the CLI `--profile` flag → Always prefix with `env -u DATABRICKS_HOST -u DATABRICKS_TOKEN -u DATABRICKS_CONFIG_PROFILE databricks [cmd] --profile [profile]`
- **Wrong workspace silent failure** → CLI commands succeed but target the wrong workspace → Verify with `databricks workspace get-status /` before bulk operations

## Serverless Compute

- **`cache()` / `persist()` crashes serverless** → `PERSIST TABLE not supported on serverless` → Use temp views or recompute
- **`DEFAULT` columns in CREATE TABLE fail** → `delta.feature.allowColumnDefaults` not enabled on most serverless clusters → Use explicit INSERT values instead
- **`browserHostName().get()` throws in jobs** → Only works in notebook interactive mode → Hardcode `WORKSPACE_HOST` in job context
- **All-None columns fail schema inference** → `createDataFrame()` with inferred schema returns all-null column types → Always use explicit `StructType`
- **`# COMMAND ----------` splits cells unconditionally** → Databricks notebook parser splits here unconditionally → if/else blocks CANNOT span this boundary; restructure logic within a single cell
- **`%pip install` must be first cell** → Re-installs after `restartPython()` reset the namespace → Put `%pip install` + `restartPython()` as the very first cell

## Delta / SQL

- **`DESCRIBE` before MERGE** → Column name mismatch causes silent data loss or schema errors → Always `DESCRIBE {table}` and match column names exactly before writing MERGE statements
- **Vector Search indexes aren't queryable tables** → Can't `DESCRIBE` or `SELECT` from a VS index directly → Query via REST API; join to source tables for full data
- **`wait_timeout` max is 50s** → Statement Execution API hard cap — not 60s → Use `wait_timeout=0s` + async polling for safety

## Databricks Apps

- **`apps update` replaces ALL resources** → It's a full replace, NOT additive → Always pass the complete resource list when calling `apps update`
- **`${var.x}` not resolved in `app.yaml`** → Bundle variables only resolve in `databricks.yml` and `resources/*.yml`, not `app.yaml` → Hardcode values or pass via environment variables in app code
- **Removing a Lakebase binding drops the SP role** → Restoring the binding recreates it, but downstream permissions may need re-granting

## DABs / Deployment

- **`bundle run --var` doesn't rebake parameters** → Must `bundle deploy --var` first to update job definitions → Always deploy before run when changing variables
- **Deploy to prod without validate** → Can push invalid cluster configs → Always run `bundle validate` before deploying to production targets

## Model Serving / Vector Search

- **VS provisioning takes ~29-30 min** → "Pending endpoint provisioning" is normal → Don't debug prematurely; poll status and wait
- **`tool_result` strict ID matching** → Every `tool_use` block needs a matching `tool_result` with the same ID → Use explicit dict format for tool results, not `.model_dump()`

## Agent / Automation

- **Cheap models ignore tool restriction prompts** → Models like Haiku will call tools you didn't allow in the prompt → Restrict `allowed_tools` lists strictly; bypass the agent for pure retrieval tasks
- **MUI dynamic IDs** → IDs like `mui-6`, `mui-10` change per render cycle → Find elements by role or label, never hardcode numeric MUI IDs

---

*Add entries here as you discover them. Promote from project-level gotchas.md when a pitfall appears in 2+ projects.*
