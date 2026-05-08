# 2026-01-01 | Claude Code | Bootstrap — initial schema harvest

> Example episodic log. Delete this file before using the template.

## Task
Bootstrap the DeepWiki memory system for this project. Populate schemas.md
from the live catalog and seed the changelog with recent session history.

## What Was Done
- Listed all tables in `my_catalog.my_schema` using `databricks tables list`
- Found 7 tables: events_raw, events_silver, dim_user, dim_product,
  fact_orders, ml_features, model_predictions
- Wrote full schema entries for all 7 tables in `memory/semantic/schemas.md`
- Ran `databricks serving-endpoints list` — found 1 active endpoint:
  `my-model-v1` (READY)
- Ran `databricks registered-models list` — 2 registered models:
  `customer-churn-v1`, `product-rec-v2`
- Seeded changelog with 3 reconstructed entries from conversation history

## What Was Skipped or Deferred
- Did not run validation (self-validation Prompt 6) — running out of context
- Did not populate `context/codebase_map.md` — next session task

## Raw Observations
- `dim_product` has a comment in the catalog: "deprecated, use dim_product_v2"
  → marked deprecated in schemas.md, but dim_product_v2 doesn't exist yet in catalog
  → this is a discrepancy to watch
- `ml_features` has 47 columns — summarized as "feature store table, 47 numeric features"
  rather than listing all of them. Full column list is in the catalog.

## Files Touched
- `memory/semantic/schemas.md` — created with 7 table entries + 2 models + 1 endpoint
- `memory/changelog.md` — seeded with 3 reconstructed entries

## Open State
- `context/codebase_map.md` is empty — needs population next session
- `dim_product` deprecation status needs resolution — does v2 exist somewhere?
- Validation step (Prompt 6) not run — do at start of next session
