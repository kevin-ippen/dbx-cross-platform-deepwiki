# DeepWiki Core Agent Instructions

> Paste into any agent harness that can read and write files. This is intentionally independent of model vendor, IDE, MCP availability, or execution environment.

## Start Of Every Task

1. Read `CORE_PROTOCOL.md` if available; otherwise read `workspace/AGENT_PROTOCOL.md`.
2. Fuzzy-resolve the requested project name against existing `projects/{name}/` folders before creating or writing memory.
3. Load the project memory slice:
   - `NORTH_STAR.md`
   - `planning/goals.md`
   - `planning/phases.md`
   - last 3 changelog entries
   - most recent 1-2 episodic log tails
   - `memory/semantic/schemas.md`
   - `memory/semantic/gotchas.md`
4. State the phase/goal, plan, regression risk, and scope before changing files or data.
5. Append a Plan event to the episodic log before or immediately after acting.

## During Work

- Append Checkpoint events after meaningful progress, plan changes, verification commands, long-running jobs, or recovery paths.
- Update semantic schemas immediately when a schema/API/data contract changes.
- Add reusable failures or traps to gotchas.
- Keep memory writes scoped to the exact canonical project name. If the project name is approximate or ambiguous, resolve first and retry with the exact name.

## Closeout

1. Append a final Close event to the episodic log.
2. Append a changelog entry with:
   - Changes
   - Decisions
   - Schema Changes
   - Unfinished
   - Warnings for Next Session
3. Use `- None` when there is no unfinished work.
4. Sync to shared storage if the workspace uses a remote mirror.
5. Run the DeepWiki evaluator after protocol, template, or memory-system changes.

## Tool Equivalents

Use whichever surface exists in the harness:

| Need | Preferred if available | File-native fallback |
|---|---|---|
| Resolve project | `deepwiki_resolve_project` or `scripts/deepwiki_resolve_project.py` | list `projects/` and fuzzy-match names |
| Preflight | `deepwiki_preflight` | read required files directly |
| Event logging | `deepwiki_checkpoint` or `scripts/deepwiki_log_event.py event` | append Markdown event |
| Session close | `deepwiki_close_session` or `scripts/deepwiki_log_event.py close` | append Close event + changelog |
| Evaluation | `scripts/deepwiki_eval.py` / `deepwiki_eval_all.py` | inspect required files and recent logs manually |
