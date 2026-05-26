# Genie Code / DBSQL Assistant Instructions

> Paste this into your Genie Code "Custom Instructions" or system prompt.
> It tells Genie how to use the DeepWiki memory system.

---

## DeepWiki — Persistent Memory System

This workspace uses a structured memory system stored in a UC Volume. It persists across sessions and platforms — Claude Code, Genie Code, and custom agents all share the same store.

**At session start:** Call `deepwiki_resolve_project(project="{project-name}")` if the name may be approximate, then call `deepwiki_preflight(project="{resolved-project}")` to load all context in one call. It returns: the agent protocol, workspace gotchas, project changelog (last 3 entries), recent bounded episodic log excerpts, project schemas, and project goals.

**During work:** Call `deepwiki_checkpoint` or `deepwiki_episodic` after stating a plan, changing a plan, completing a meaningful step, starting a long-running job, choosing an error path, or discovering a durable fact.

**Write safety:** Discovery tools may fuzzy-resolve project names. Write tools must use the exact canonical project name returned by resolution; if resolution is ambiguous, ask instead of writing.

**At session end:** If you changed anything (code, schema, approach), call `deepwiki_close_session` to write a final episodic close event and changelog entry together.

**Volume paths (if reading directly):**
- Workspace: `/Volumes/{catalog}/{schema}/{volume}/workspace/`
- Projects: `/Volumes/{catalog}/{schema}/{volume}/projects/{project-name}/`

**When to read what:**

| Need | Read |
|------|------|
| Current schema state | `projects/{name}/memory/semantic/schemas.md` |
| Platform pitfalls | `workspace/memory/semantic/gotchas.md` |
| What happened recently | `projects/{name}/memory/changelog.md` (last 3 entries) |
| In-flight state | `projects/{name}/memory/episodic/` (most recent 1-2 files) |
| Cross-project dependencies | `workspace/context/cross_references.md` |
| Project landscape | `workspace/PROJECT_INDEX.md` |

**Before acting:** State which phase and goal your work advances. If you can't connect it to a goal, ask.

**Before any schema change:** Check `context/cross_references.md` for downstream consumers.

---

*Replace `{catalog}`, `{schema}`, `{volume}`, and `{project-name}` with your actual values.*
