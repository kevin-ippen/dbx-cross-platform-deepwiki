# Episodic Log - 2026-01-01 | Claude Code | Bootstrap schema harvest

> Example episodic log. Delete this file before using the template.

## Timeline

### 09:12:04 - Plan: Bootstrap DeepWiki memory

#### Objective
- Populate deterministic project memory from the live catalog and recent session history.

#### Plan
- Read AGENT_PROTOCOL, gotchas, patterns, goals, phases, and the latest changelog entries.
- Inspect catalog resources needed for `memory/semantic/schemas.md`.
- Seed the changelog only after the schema harvest is verified.

### 09:31:22 - Checkpoint: Catalog harvest complete

#### Status
- Listed all tables in `my_catalog.my_schema`.
- Found 7 tables: `events_raw`, `events_silver`, `dim_user`, `dim_product`, `fact_orders`, `ml_features`, `model_predictions`.
- Found 1 active serving endpoint: `my-model-v1` (READY).
- Found 2 registered models: `customer-churn-v1`, `product-rec-v2`.

#### Files Touched
- `memory/semantic/schemas.md`

#### Commands / Verification
- `databricks tables list my_catalog.my_schema`: passed, 7 tables found.
- `databricks serving-endpoints list`: passed, 1 ready endpoint found.
- `databricks registered-models list`: passed, 2 models found.

#### Decisions / Rationale
- Summarized `ml_features` as a feature table instead of listing all 47 numeric feature columns inline.

#### Surprises / Failures
- `dim_product` is marked deprecated in catalog comments, but `dim_product_v2` was not found.

#### Unresolved / Next
- [ ] Populate `context/codebase_map.md`.
- [ ] Resolve whether `dim_product_v2` exists in another schema.

### 10:02:47 - Close: Bootstrap memory seeded

#### Status
- Wrote schema entries for 7 tables, 2 models, and 1 endpoint.
- Seeded changelog with reconstructed recent session history.

#### Files Touched
- `memory/semantic/schemas.md`
- `memory/changelog.md`

#### Commands / Verification
- Manual review of `memory/semantic/schemas.md`: passed for discovered resources.

#### Warnings
- Run the validation prompt at the start of the next session because this bootstrap did not include a full self-validation pass.
