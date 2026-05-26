# Bootstrap Guide — Populating Your First Project

This is a prompt sequence to paste into your agent (Claude Code, Genie Code, or Codex) in order.
Run them once when setting up a new project. After bootstrap, normal sessions follow `AGENT_PROTOCOL.md`.

**Prerequisites before starting:**
- You've run `bootstrap.sh` to scaffold the directory structure
- You've filled in `NORTH_STAR.md`, `planning/goals.md`, and `planning/phases.md` by hand (these are human-owned)
- Your agent has access to the Databricks CLI and your workspace

---

## Prompt 0 — Orient the Agent

```
Before we begin any work, I need you to understand a new system we're implementing.
Read every file in .deepwiki/ — start with AGENT_PROTOCOL.md, then NORTH_STAR.md,
then planning/goals.md and phases.md.

From this point forward, every session (including this one) follows the Agent Protocol.
You will read before acting, connect work to goals, append episodic plan/status/checkpoint
events during work, and write a changelog entry plus final episodic close before we end.

Confirm you've read and understood the protocol, then tell me:
1. What is this project's north star?
2. What phase are we in?
3. What are the active goals?
```

> Wait for confirmation. Correct any misunderstanding. This calibrates the agent
> and verifies the files are readable from its environment.

---

## Prompt 1 — Schema Harvest

```
Our first bootstrap task: populate .deepwiki/memory/semantic/schemas.md
with ground-truth schema state from the Databricks catalog.

1. Use the Databricks CLI or SDK to list all tables in:
   - {catalog}.{schema}
   (add additional schemas as needed)

2. For each table, get:
   - Column names and data types
   - Table comment/description if one exists
   - Whether it's managed or external
   - Last modified timestamp if available

3. Write results into .deepwiki/memory/semantic/schemas.md using the
   template format already in that file. For each table include:
   - Status: active (mark deprecated if name contains _old, _bak, _deprecated)
   - Purpose: infer from table name and columns; use comment if available
   - Key Columns: all columns with types
   - Last Modified: from metadata if available

4. Also check for:
   - Any views in these schemas
   - Registered models: databricks registered-models list
   - Serving endpoints: databricks serving-endpoints list

5. Write models and endpoints into the Models/Endpoints section of schemas.md.

Don't summarize or truncate — this file is our single source of truth for schema state.
```

> Review the output. Fix obvious errors. Accuracy here prevents schema-bricking later.

---

## Prompt 2 — Codebase Map

```
Next: populate .deepwiki/context/codebase_map.md.

1. List the project root directory structure. Note the top-level layout
   in the "Repository / Workspace Layout" section.

2. For each Python file, notebook, or config file:
   - Note its path and infer its purpose from the filename and first ~30 lines
   - Note what tables/schemas it references
   - Note any TODOs, FIXMEs, or HACKs

   For files over 200 lines, just read the first 50 lines and imports —
   don't load the whole file into your context.

3. Populate the "Key Files" table with the 10 most important files.

4. Populate "Where Things Run":
   - Files in a workflows/ or jobs/ directory → Databricks Workflow
   - Notebooks → Databricks Notebook
   - Files with a main() or CLI entrypoint → local/CLI

5. If there's a databricks.yml or bundle config, also populate
   .deepwiki/context/dab_manifest.md with the bundle structure,
   targets, and resources defined in it.
```

---

## Prompt 3 — Stack & Integrations

```
Next: populate .deepwiki/context/stack.md and .deepwiki/context/integrations.md.

For stack.md:
- Check Databricks runtime version from cluster configs or databricks.yml
- Check Python version and key library versions from requirements.txt,
  setup.py, pyproject.toml, or conda.yml
- Note the cloud provider from the workspace URL

For integrations.md:
- Scan the code for external API calls or service integrations
  (requests., httpx., sqlalchemy., boto3., azure., google.cloud., etc.)
- For each one found: what service, how it authenticates, what it's used for
- Check for any Databricks secret scopes that hint at integrations:
  databricks secrets list-scopes
  (don't retrieve secret values, just note the key names)
```

---

## Prompt 4 — Seed the Changelog from Recent History

```
Now I need to seed .deepwiki/memory/changelog.md with recent history.
I'm going to describe what happened in my recent sessions. For each one,
write a changelog entry using the standard format from the protocol.

Here are my recent sessions:

---
Session ~{date}: {Platform used}
{Your rough summary — stream of consciousness is fine.
 Example: "Switched ingest layer to structured streaming. Added loyalty_tier
 column to dim_customer. Updated DAB bundle. Didn't finish updating the
 downstream reporting notebook."}
---

Write each as a properly formatted changelog entry, newest first.
Infer schema changes from what I described.
For anything ambiguous, flag it with [VERIFY] so I can correct it.

After writing the changelog entries: are there any gotchas you can extract
from what I described? If so, add them to .deepwiki/memory/semantic/gotchas.md.
```

> If you have actual chat logs or notebook outputs from recent sessions,
> paste excerpts instead of writing summaries — the agent will extract the relevant bits.

---

## Prompt 5 — First Compilation Pass

```
Run a compilation pass over everything we've built so far.

Read through:
- All entries in memory/changelog.md
- The current state of memory/semantic/schemas.md
- The codebase_map and any gotchas already written

Now produce or update:

1. memory/semantic/patterns.md — Are there any recurring patterns visible
   from the changelog and codebase scan? Naming conventions, code organization,
   deployment patterns? Only add patterns that appear consistently, not one-offs.

2. memory/semantic/gotchas.md — Any additional lessons or anti-patterns visible
   from the changelog that you haven't captured yet?

3. memory/semantic/domain_glossary.md — Any domain-specific terms from the
   codebase or session descriptions that might be ambiguous to a future agent?

Keep each file within its token budget:
- patterns.md: <300 words
- gotchas.md: <300 words
- domain_glossary.md: <200 words

Dense and current beats comprehensive and stale.
```

---

## Prompt 6 — Self-Validation

```
Final bootstrap step. Validate the memory system against itself.

1. Read schemas.md. Pick 3 tables at random. Use the Databricks CLI to
   verify they actually exist and the columns match what we recorded.
   Report any discrepancies.

2. Read codebase_map.md. Pick 3 files listed as "key files." Verify they
   exist at the listed paths. Read their first 20 lines and confirm the
   stated purpose is accurate.

3. Read the changelog entries. Do any reference tables or files that aren't
   in schemas.md or codebase_map.md? If so, either the changelog has stale
   references or we missed something.

4. Check the context budget. Report the approximate word count of each
   mandatory pre-flight file. Flag any that exceed budget:
   - NORTH_STAR.md: <500 words
   - goals.md: <300 words
   - phases.md: <400 words
   - changelog (last 3 entries combined): <600 words total
   - schemas.md: <500 words
   - gotchas.md: <300 words

   These budgets keep total pre-flight under ~4,000 tokens — small enough
   to leave room for actual work in any context window.

Report results and fix any issues found.
```

---

## Prompt 7 — Close the Bootstrap Session

```
We're ending this session. Follow the session close protocol:

1. Append a changelog entry to memory/changelog.md for this bootstrap session.
   Document what we built, what we populated, and any issues found in validation.

2. Write a final episodic close event to memory/episodic/YYYY-MM-DD_{platform}_{slug}.md.
   Include more detail than the changelog: what you tried, what surprised you,
   what's still uncertain.

3. Note any warnings for the next session.

4. Write a session handoff note at agents/session_handoff.md summarizing
   current project state and what the next session should focus on
   (based on goals.md and phases.md).
```

---

## The Test (Start of Session 2)

Open a fresh agent session and paste only this:

```
Read .deepwiki/AGENT_PROTOCOL.md and execute the pre-flight checklist.
Then tell me: what's the current state of this project, what was done
last session, and what should we focus on today?
```

If the agent correctly reconstructs project state from the memory files alone —
without you explaining anything — the bootstrap worked.

---

## Ongoing Maintenance

| When | What to Do |
|------|-----------|
| During every session | Append episodic plan/status/checkpoint events |
| Every session end | Append final episodic close + append to `changelog.md` |
| Every 3-5 sessions | Ask agent to compile episodic logs → semantic memory |
| At phase boundaries | Compile, then update `goals.md` and `phases.md` |
| When a gotcha appears in 2+ projects | Promote to `workspace/memory/semantic/gotchas.md` |
| Monthly | Run cross-project harmonization (see below) |

## Cross-Project Harmonization (After 2+ Projects Are Bootstrapped)

Once you have multiple projects running, run this in Genie Code or Claude Code
to build the workspace-level memory that connects them:

**H1:** Build `workspace/PROJECT_INDEX.md` and `workspace/context/catalog_map.md`
by reading each project's NORTH_STAR and schemas, then scanning the full catalog.

**H2:** Discover cross-project dependencies by comparing schemas across projects
and checking query history for joins across schemas.

**H3:** Promote shared knowledge — patterns and gotchas that appear in 2+ projects
move to `workspace/memory/semantic/`. Log in `workspace/promotion_log.md`.

**H4:** Schema conflict detection — find tables documented differently across projects,
deprecated tables still referenced elsewhere, orphaned tables with no owner.

**H5:** Write a workspace-level changelog entry documenting what harmonization found.

Repeat H1-H5 whenever a new project is bootstrapped or monthly as maintenance.
