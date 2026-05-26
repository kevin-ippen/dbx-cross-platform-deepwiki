# Agent Protocol - Project Level

Follow `workspace/AGENT_PROTOCOL.md` first. This project protocol adds local recovery and closeout requirements.

## Before Acting

0. Confirm the requested project name exactly matches this project's canonical directory name before writing memory here. If the name was approximate, resolve it first and retry with the canonical name.
1. Read `NORTH_STAR.md`, `planning/goals.md`, and `planning/phases.md`.
2. Read the last 3 entries in `memory/changelog.md`.
3. Read the most recent 1-2 tails/capped excerpts under `memory/episodic/` for in-flight recovery.
4. Read `memory/semantic/schemas.md` and `memory/semantic/gotchas.md` before touching data contracts, app behavior, or platform resources.
5. State the phase/goal, planned change, regression risk, and scope before editing.

## During Work

- Append plan/status/checkpoint events to `memory/episodic/YYYY-MM-DD_{platform}_{slug}.md` whenever the plan changes, a meaningful step completes, a job starts, an error path is chosen, or interruption risk appears.
- If the workspace includes `scripts/deepwiki_log_event.py`, use it. Otherwise call the MCP `deepwiki_checkpoint`/`deepwiki_episodic` tool or append the event manually.
- Write a verification checkpoint when a test, build, deploy, eval, or manual check passes or fails.
- Update `memory/semantic/schemas.md` immediately for schema/API contract changes.
- Append reusable surprises to `memory/semantic/gotchas.md`.

## Closeout

- Append a final episodic close event before writing the changelog.
- Append `memory/changelog.md` with changes, decisions, schema changes, unfinished items, and warnings. Use `- None` for no unfinished work.
- Sync `.deepwiki/` to shared storage if this project uses a remote mirror.
- If this session changed memory protocols, templates, or harness scripts, run `scripts/deepwiki_eval.py` and report any low handoff, missing event-type, or unevaluated mirror findings.
