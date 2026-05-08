# Infrastructure Stack

> Workspaces, warehouses, compute profiles, and FMAPI endpoints.
> Keep this current — agents use it to pick the right profile and resource ID.

## Databricks Workspaces

| Profile Name | Workspace URL | Cloud | Use |
|-------------|--------------|-------|-----|
| `dev-workspace` | `https://{your-adb-id}.azuredatabricks.net` | Azure | Development / experiments |
| `prod-workspace` | `https://{your-adb-id}.azuredatabricks.net` | Azure | Production pipelines |

*Replace with your actual profiles from `~/.databrickscfg`.*

## SQL Warehouses

| Profile | Warehouse Name | Warehouse ID | Use |
|---------|---------------|-------------|-----|
| `dev-workspace` | Shared SQL Endpoint | `{warehouse-id}` | Ad-hoc SQL, notebooks |
| `prod-workspace` | Production SQL | `{warehouse-id}` | Production queries |

*Get warehouse IDs from: Databricks UI → SQL → SQL Warehouses → copy the ID from the URL.*

## FMAPI (Foundation Model Endpoints)

Databricks-hosted models available via the serving endpoint. Call with OpenAI-compatible SDK pointing at `https://{workspace-host}/serving-endpoints`.

| Model ID | Description | Use |
|----------|-------------|-----|
| `databricks-claude-sonnet-4-6` | Claude Sonnet 4.6 | Writing, complex reasoning |
| `databricks-claude-haiku-4-5` | Claude Haiku 4.5 | Fast, cheap summarization/skimming |
| `databricks-meta-llama-3-3-70b-instruct` | Llama 3.3 70B | Open-source alternative |
| `databricks-mixtral-8x7b-instruct` | Mixtral 8x7B | Cheapest option for simple tasks |
| `databricks-gte-large-en` | GTE Large EN | Embeddings |

*Available models vary by workspace. Check: Databricks UI → Serving → Foundation Model APIs.*

## UC Catalog Structure

| Catalog | Description |
|---------|-------------|
| `{your_catalog}` | *(describe your primary catalog)* |

---

*Update this file when you add a workspace, warehouse, or model endpoint.*
