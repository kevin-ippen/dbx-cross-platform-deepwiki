# Episodic Memory

> Raw session logs — the source material that gets compiled into semantic memory.
> One file per session, named `YYYY-MM-DD_{platform}.md`.
> Never edit these after writing them. They are the immutable record.

## File Naming

```
2026-05-08_claude-code.md
2026-05-09_genie-code.md
2026-05-10_codex.md
```

## What Goes Here vs. changelog.md

| changelog.md | episodic/{date}_{platform}.md |
|---|---|
| Structured, formatted summary | Raw, verbose session log |
| Every agent reads this | Feeds into compilation only |
| Stays small (last N entries) | Accumulates; archive after 30 days |
| The "what changed" story | The "how we got there" record |

`changelog.md` is your fast-path read. Episodic logs are the audit trail.
If changelog.md ever needs correction, the episodic log is the source of truth.

## Entry Format

```markdown
# YYYY-MM-DD | {Platform} | {Brief title}

## Task
What the session was trying to accomplish.

## What Was Done
- Step-by-step: what was attempted, what worked, what was changed
- Include specific file paths, table names, function names

## What Was Skipped or Deferred
- What you started but didn't finish and why

## Raw Observations
- Unexpected behavior encountered
- Things that worked surprisingly well or badly
- Dead ends worth noting so you don't retread them
- Any uncertainty about whether a step worked correctly

## Files Touched
- path/to/file.py — what changed
- another/file.sql — what changed

## Open State
- What's mid-flight that the next agent needs to know
```

## Archival

After 30 days, move to `episodic/archive/`. Semantic memory compiled from
archived episodes stays current — the archive is for auditing, not loading.

## Compilation Trigger

When this directory has 3-5 uncompiled entries (entries newer than the last
`memory/semantic/` update), ask your agent to compile:

> "Compile episodic logs since [last compile date] into updated semantic memory.
> Use the template in `agents/delegation_templates/memory_compiler.md`."
