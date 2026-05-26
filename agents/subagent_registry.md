# Subagent Registry

> Catalog of reusable subagent patterns. Director agents reference these when delegating work.
> Each entry defines: purpose, model tier, memory slice (what context to provide), and output format.

## file_skimmer
- **Purpose:** Read a large file and return a structured summary without loading it into the director's context
- **Model Tier:** Cheap (Llama / Mixtral via Databricks FMAPI, or Claude Haiku)
- **Memory Slice:** None — stateless by design
- **Input:** File path + specific questions to answer about the file
- **Output Format:** Structured summary: purpose, key functions/classes, dependencies, notable patterns
- **Token Budget:** ~500 tokens output
- **Template:** `delegation_templates/file_skimmer.md`

## schema_validator
- **Purpose:** Verify that code references match the current schema state before deploying
- **Model Tier:** Cheap
- **Memory Slice:** `memory/semantic/schemas.md`
- **Input:** File(s) to validate + schemas.md contents
- **Output Format:** List of valid/invalid references with line numbers
- **Template:** `delegation_templates/schema_validator.md`

## code_reviewer
- **Purpose:** Review code for adherence to project patterns and known gotchas
- **Model Tier:** Mid (Claude Haiku / Sonnet via Databricks)
- **Memory Slice:** `memory/semantic/patterns.md` + `memory/semantic/gotchas.md`
- **Input:** Code diff or file(s) + patterns + gotchas
- **Output Format:** Issues list with severity (critical / warning / suggestion)
- **Template:** `delegation_templates/code_reviewer.md`

## memory_compiler
- **Purpose:** Compile episodic flight-recorder logs and changelog entries into updated semantic memory files
- **Model Tier:** Mid
- **Memory Slice:** All `memory/episodic/` and `memory/changelog.md` entries in date range + current `memory/semantic/*.md` files
- **Input:** Episodic logs + changelog entries + current semantic files
- **Output Format:** Updated semantic memory files (schemas, patterns, gotchas, glossary)
- **Template:** `delegation_templates/memory_compiler.md`
- **When to Run:** Every 3-5 sessions, after schema changes, before phase boundaries

## test_writer
- **Purpose:** Generate tests for a module based on project conventions
- **Model Tier:** Mid-high
- **Memory Slice:** `memory/semantic/patterns.md` (testing section) + `memory/semantic/schemas.md`
- **Input:** Module to test + patterns + schemas
- **Output Format:** Test file following project conventions

## cross_project_lookup
- **Purpose:** Find schema/asset info from another project's `.deepwiki/` without guest-writing to it
- **Model Tier:** Director-level (needs reasoning about dependencies)
- **Memory Slice:** `workspace/PROJECT_INDEX.md` + `workspace/context/cross_references.md` + target project's `schemas.md`
- **Input:** Asset name/path + what info is needed
- **Output Format:** Relevant schema details + consumer/owner info + dependency warnings

---

*Add entries here when you create a new reusable subagent pattern.*
