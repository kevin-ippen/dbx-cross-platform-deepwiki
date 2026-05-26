# DeepWiki Core Protocol

> Model-agnostic, harness-agnostic operating contract for any agent that can read and write files. MCP tools, CLI helpers, IDE hooks, notebooks, and manual edits are implementation details; the behavior below is the portable core.

## Non-Negotiable Invariants

1. **Resolve project identity before work.** Fuzzy-search existing project names before creating or writing memory for a project. If the intended project is ambiguous, ask or require the exact canonical project directory name.
2. **Read before acting.** Load workspace protocol, project goals, recent changelog, recent episodic log tail, schemas, and gotchas before changing code, data, or decisions.
3. **Connect work to goals.** State the phase/goal, planned action, regression risk, and scope before editing.
4. **Write in-flight state continuously.** Record Plan, Checkpoint, error/recovery, verification, and Close events in episodic memory. A session that crashes should still be reconstructable.
5. **Fail closed on writes.** Approximate project names are allowed for discovery/read flows, but changelog/checkpoint/close writes must target an exact project identity.
6. **Keep preflight bounded.** Load the most recent 1-2 episodic logs as tails/capped excerpts, not unbounded raw history.
7. **Separate raw and compiled memory.** Episodic logs are the flight recorder. Changelog is the structured summary. Semantic memory is compiled durable fact.
8. **Measure the memory system.** Run deterministic scorecards after protocol, template, or memory-system changes; treat low handoff, missing event types, and skipped remote mirror checks as findings.
9. **Report residual risk explicitly.** Local freshness is not proof of remote sync. Missing behavioral cold-resume tests, unevaluated mirrors, and unvalidated hooks must be visible.

## Minimal Harness Contract

Every harness should provide one of these equivalent surfaces:

| Need | File-native | CLI helper | MCP/tool equivalent |
|---|---|---|---|
| Resolve project | List `projects/` and fuzzy match names | `scripts/deepwiki_resolve_project.py` | `deepwiki_resolve_project` |
| Preflight | Read protocol + project slice | direct file reads | `deepwiki_preflight` |
| Log in-flight event | Append episodic event | `scripts/deepwiki_log_event.py event` | `deepwiki_checkpoint` / `deepwiki_episodic` |
| Close session | Append close + changelog | `scripts/deepwiki_log_event.py close` | `deepwiki_close_session` |
| Evaluate health | Inspect files + metadata | `scripts/deepwiki_eval.py` / `deepwiki_eval_all.py` | harness-specific wrapper |

If a harness cannot call tools, it can still comply by reading and writing the Markdown files directly.

## Project Resolution Rules

- Canonical project identity is the directory under `projects/{name}/`.
- Fuzzy matching is for **discovery** and duplicate prevention.
- Writes require exact canonical identity. Examples:
  - `lakefind` → write allowed when `projects/lakefind/` exists.
  - `lake find` → resolve first; write blocked until retried as `lakefind`.
  - `lakefind public` with `lakefind` and `lakefind-public` nearby → ambiguous; ask or require exact name.
- Before creating `projects/new-name/`, run fuzzy resolution against existing projects and document why this is a new project.

## Preflight Load Order

1. Workspace:
   - `workspace/AGENT_PROTOCOL.md`
   - `workspace/PROJECT_INDEX.md`
   - `workspace/memory/semantic/gotchas.md`
   - `workspace/memory/semantic/patterns.md`
2. Project:
   - `projects/{name}/NORTH_STAR.md`
   - `projects/{name}/planning/goals.md`
   - `projects/{name}/planning/phases.md`
   - Last 3 entries from `projects/{name}/memory/changelog.md`
   - Most recent 1-2 episodic log tails from `projects/{name}/memory/episodic/`
   - `projects/{name}/memory/semantic/schemas.md`
   - `projects/{name}/memory/semantic/gotchas.md`
3. Task-specific:
   - `workspace/context/cross_references.md` for shared assets
   - `workspace/context/catalog_map.md` for schema/data work
   - `workspace/context/integrations.md` for external services
   - `workspace/context/stack.md` for infrastructure

## Flight-Recorder Event Cadence

Append an episodic event when any of these happen:

- Initial plan is stated.
- Plan changes.
- A meaningful step completes.
- A long-running job, deploy, or evaluation starts.
- A surprising failure or recovery path appears.
- A durable fact, schema/API contract, or decision is discovered.
- A verification command passes or fails.
- The session closes.

Use this portable event shape:

```markdown
### HH:MM:SS - Plan|Checkpoint|Close: Brief summary

#### Objective
- Why this work exists

#### Plan
- Current intended steps

#### Status
- What changed or what is in progress

#### Files Touched
- `path/to/file`

#### Commands / Verification
- `command`: result

#### Decisions / Rationale
- Choice and reason

#### Surprises / Failures
- What went wrong and how it was handled

#### Unresolved / Next
- [ ] Concrete next action

#### Warnings
- What the next agent must know
```

Only include sections that have content. For no unfinished work in changelog entries, write `- None`, not `- [ ] None`.

## Evaluation Standard

Run scorecards whenever you change the memory protocol, bootstrap templates, harness tools, or project memory rollout:

```bash
python3 scripts/deepwiki_eval.py --deepwiki-root projects/{name} --project-root /path/to/project --project {name}
python3 scripts/deepwiki_eval_all.py --base-dir /path/to/projects
```

Useful thresholds:

| Dimension | Target | Watch If |
|---|---:|---:|
| Retrieval utility | >= 85 | < 70 |
| Protocol compliance | >= 90 | < 80 |
| Handoff quality | >= 80 | < 70 |
| Drift freshness | >= 85 | < 70 or remote mirror not evaluated |
| Efficiency | >= 80 | < 70 |

The deterministic scorecard is not a full behavioral proof. For high-confidence rollout, also run a cold-resume test with a fresh agent: provide only the preflight instruction and ask it to reconstruct current state, recent changes, risks, and next action.

## Sharing Readiness

A DeepWiki system is ready to share internally when:

- Core docs and templates describe the same protocol.
- Write paths fail closed on ambiguous project names.
- Recent episodic logs contain Plan, Checkpoint, and Close events.
- Changelog entries include changes, decisions, schema changes, unfinished work, and warnings.
- Scorecards pass or clearly explain gaps.
- Remote mirror/deployment status is either verified or explicitly called out as unevaluated.
