# Episodic Memory

> Raw session logs — the source material that gets compiled into semantic memory.
> One file per session or task thread, named `YYYY-MM-DD_{platform}_{slug}.md`.
> Append throughout the session. Treat it as a flight recorder for interruption recovery.

## File Naming

```
2026-05-08_claude-code_streaming-investigation.md
2026-05-09_genie-code_schema-validation.md
2026-05-10_codex_flight-recorder-rollout.md
```

## What Goes Here vs. changelog.md

| changelog.md | episodic/{date}_{platform}.md |
|---|---|
| Structured, formatted summary | In-flight plan/status/checkpoint log |
| Every agent reads this | Recent 1-2 files read during pre-flight; older files feed compilation |
| Stays small (last N entries) | Accumulates; archive after 30 days |
| The "what changed" story | The "how we got there" record |

`changelog.md` is your fast-path read. Episodic logs are the audit trail.
If changelog.md ever needs correction, the episodic log is the source of truth.

## Event Format

```markdown
# Episodic Log - YYYY-MM-DD | {Platform} | {Brief title}

## Timeline

### HH:MM:SS - Plan: {Brief summary}

#### Objective
- What the session is trying to accomplish

#### Plan
- Immediate steps

### HH:MM:SS - Checkpoint: {Brief summary}

#### Status
- What changed or what is in progress

#### Commands / Verification
- `command`: result

#### Unresolved / Next
- [ ] Immediate next step
```

Expected recent-session coverage:

- At least one `Plan` event near the start.
- At least one `Checkpoint` event for meaningful progress or verification.
- One final `Close` event before the changelog entry.
- Enough structured sections for another agent to resume without asking what happened.

## Archival

After 30 days, move to `episodic/archive/`. Semantic memory compiled from
archived episodes stays current — the archive is for auditing, not loading.

## Compilation Trigger

When this directory has 3-5 uncompiled entries (entries newer than the last
`memory/semantic/` update), ask your agent to compile:

> "Compile episodic logs since [last compile date] into updated semantic memory.
> Use the template in `agents/delegation_templates/memory_compiler.md`."
