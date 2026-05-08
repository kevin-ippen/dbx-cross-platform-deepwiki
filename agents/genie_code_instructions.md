# Genie Code / DBSQL Assistant Instructions

> Paste this into your Genie Code "Custom Instructions" or system prompt.
> It tells Genie how to use the DeepWiki memory system.

---

## DeepWiki — Persistent Memory System

This workspace uses a structured memory system stored in a UC Volume. It persists across sessions and platforms — Claude Code, Genie Code, and custom agents all share the same store.

**At session start:** Call `deepwiki_preflight(project="{project-name}")` to load all context in one call. It returns: the agent protocol, workspace gotchas, project changelog (last 3 entries), project schemas, and project goals.

**At session end:** If you changed anything (code, schema, approach), call `deepwiki_changelog` to record what happened. Use the format from the protocol.

**Volume paths (if reading directly):**
- Workspace: `/Volumes/{catalog}/{schema}/{volume}/workspace/`
- Projects: `/Volumes/{catalog}/{schema}/{volume}/projects/{project-name}/`

**When to read what:**

| Need | Read |
|------|------|
| Current schema state | `projects/{name}/memory/semantic/schemas.md` |
| Platform pitfalls | `workspace/memory/semantic/gotchas.md` |
| What happened recently | `projects/{name}/memory/changelog.md` (last 3 entries) |
| Cross-project dependencies | `workspace/context/cross_references.md` |
| Project landscape | `workspace/PROJECT_INDEX.md` |

**Before acting:** State which phase and goal your work advances. If you can't connect it to a goal, ask.

**Before any schema change:** Check `context/cross_references.md` for downstream consumers.

---

*Replace `{catalog}`, `{schema}`, `{volume}`, and `{project-name}` with your actual values.*
