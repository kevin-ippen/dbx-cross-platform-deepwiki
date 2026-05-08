# Agent Protocol — Workspace Level

> This file is MANDATORY reading for any agent session in this workspace.
> It SUPERSEDES project-level AGENT_PROTOCOL.md for cross-project rules.
> Platform-agnostic: works for Genie Code, Claude Code, Copilot, Codex, or any future agent.

## Pre-Flight Checklist

### 1. Determine Scope
- **Single project?** → Read that project's `.deepwiki/AGENT_PROTOCOL.md` if it exists; otherwise follow this file
- **Cross-project or workspace-wide?** → Follow this file's full checklist
- **New project?** → Read `PROJECT_INDEX.md` to understand the landscape first

### 2. Load Workspace Context
Read these files. Do not summarize them out loud unless asked — just internalize.
- `PROJECT_INDEX.md` — what projects exist, where, what they do
- `memory/semantic/gotchas.md` — platform-general pitfalls
- `memory/semantic/patterns.md` — conventions enforced across all projects

### 3. Load Task-Relevant Context
Only read these if relevant to the current task:
- Working across projects → `context/cross_references.md` (who owns what, who consumes what)
- Touching schemas → `context/catalog_map.md` (full catalog topology)
- Using external APIs → `context/integrations.md` (auth, endpoints, gotchas)
- Need infrastructure details → `context/stack.md` (workspaces, warehouses, FMAPI endpoints)
- Unfamiliar term → `memory/semantic/domain_glossary.md`

### 4. If Working in a Specific Project
Also load that project's `.deepwiki/` memory:
- `NORTH_STAR.md` — the why
- `planning/goals.md` — the what (current priorities)
- `planning/phases.md` — the when (execution order)
- Last 3 entries in `memory/changelog.md`
- `memory/semantic/schemas.md` — current schema state
- `memory/semantic/gotchas.md` — project-specific pitfalls

### 5. State Your Plan (Before Acting)
Before writing any code or making any changes, state:
1. Which **phase** and **goal** this work advances
2. A brief description of what you intend to do
3. Any **risks of regression** to recent changes (cross-reference changelog)
4. Estimated scope: small (single file), medium (multi-file), large (architectural)

**If you cannot connect your planned work to an active goal → STOP and ask.**

### 6. During Execution
- If you encounter a schema change: update `schemas.md` immediately, not later
- If you hit a surprising failure: note it for `gotchas.md`
- If your approach diverges from the plan stated in step 5: pause and explain why
- Periodically re-check: "Is what I'm doing still serving the active goal?"

### 7. Session Close (Before Ending)
Append to `projects/{project-name}/memory/changelog.md` using this format:

```markdown
## YYYY-MM-DD | [Agent Platform] | [Phase] - [Brief Description]

### Changes
- What was created, modified, or deleted (be specific about files)

### Decisions
- What choices were made and why (especially non-obvious ones)

### Schema Changes
- Any table, column, model, or API changes (with full paths)

### Unfinished
- [ ] What's left to do (as checklist items)

### Warnings for Next Session
- Things the next agent MUST know to avoid breaking something
```

If switching platforms next session, also write `agents/session_handoff.md`.

---

## Memory Write Rules

| Memory Tier | Who Writes | When |
|------------|-----------|------|
| `NORTH_STAR.md` | Human only | When vision changes |
| `goals.md`, `phases.md` | Human only | When priorities shift |
| `decisions.md` | Agent (with human approval) | When architectural choices are made |
| `changelog.md` | Agent (mandatory) | Every session that changes anything |
| `semantic/*.md` | Agent (compilation task) | Every 3-5 sessions or at phase boundaries |

## Subagent Rules

- Subagents **read** memory slices but **never write** to `.deepwiki/`
- The director agent curates what each subagent receives
- Subagent outputs flow back to the director for memory integration
- See `agents/subagent_registry.md` for available subagent patterns

---

## Cross-Project Context (when needed)

If your current task references a table, model, endpoint, or library that
is NOT documented in the current project's `memory/semantic/schemas.md`:

1. Read `context/cross_references.md` to find the owner project
2. Read the owner project's `schemas.md` at the path listed in `PROJECT_INDEX.md`
3. Do NOT modify the other project's `.deepwiki/` files — you are a guest
4. If you need a schema change in another project's asset, note it in
   the current project's `planning/open_questions.md` as a cross-project dependency

If your task might BREAK a downstream consumer of your schemas:
1. Read `context/cross_references.md` to find consumers
2. Check each consumer project's changelog (last 3 entries) for
   anything that depends on the schema you're changing
3. Note the risk in your changelog entry under "Warnings for Next Session"

---

## Promotion Rules (Project → Workspace)

| What to Promote | Trigger | From → To |
|----------------|---------|-----------|
| Gotchas that are platform-general | Applies beyond one project | project `gotchas.md` → workspace `gotchas.md` |
| Patterns used across projects | Pattern appears in 2+ projects | project `patterns.md` → workspace `patterns.md` |
| Domain terms that are org-wide | Term not project-specific | project glossary → workspace glossary |
| Schema entries for shared tables | Table consumed by >1 project | project `schemas.md` → `catalog_map.md` + `cross_references.md` |

- Always log promotions in `promotion_log.md`
- Keep the entry in BOTH places (project = detailed, workspace = concise)
- Promotion cadence: at phase boundaries, after new project bootstrap, when re-explaining the same concept
