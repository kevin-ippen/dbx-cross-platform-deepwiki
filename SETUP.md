# Setup Guide

## What you're setting up

A `.deepwiki/` folder in your workspace that persists agent memory across sessions and platforms. Any agent — Claude Code, Genie Code, Copilot, Codex — reads the same files and follows the same protocol.

## Option A: Local only (Claude Code / Copilot / Codex)

No Databricks required. The `.deepwiki/` folder lives alongside your project files.

```bash
# 1. Scaffold the structure
chmod +x bootstrap.sh
./bootstrap.sh --workspace my-workspace --project my-first-project

# 2. Fill in the workspace context
#    Open workspace/context/stack.md → add your Databricks profiles and warehouse IDs
#    Open workspace/PROJECT_INDEX.md → describe your project

# 3. Fill in the project context
#    Open projects/my-first-project/NORTH_STAR.md → write your goal
#    Open projects/my-first-project/planning/goals.md → list your current priorities

# 4. Wire up Claude Code (optional)
#    Add this line to your CLAUDE.md:
echo 'Read .deepwiki/workspace/AGENT_PROTOCOL.md at session start.' >> CLAUDE.md
```

## Option B: UC Volume (Genie Code + multi-platform sync)

Stores DeepWiki on a Unity Catalog Volume so every agent — local Claude Code AND Genie Code in the browser — reads the same files.

```bash
# 1. Create the volume
databricks sql execute --warehouse {warehouse-id} \
  "CREATE VOLUME IF NOT EXISTS {catalog}.{schema}.deepwiki"

# 2. Upload the workspace template
databricks fs cp -r workspace/ \
  /Volumes/{catalog}/{schema}/deepwiki/workspace/ --recursive

# 3. Create your first project in the volume
databricks fs cp -r projects/_template/ \
  /Volumes/{catalog}/{schema}/deepwiki/projects/my-first-project/ --recursive

# 4. Fill in your context (edit files locally, then re-upload, or edit in Databricks UI)

# 5. Deploy the MCP server (optional but recommended for Genie Code)
cd mcp-server/
# Edit app.yaml → set DEEPWIKI_VOLUME to /Volumes/{catalog}/{schema}/deepwiki
databricks apps deploy deepwiki-mcp --source-code-path .

# 6. Register MCP server in Genie Code
#    See mcp-server/README.md for the .mcp_servers.json snippet
```

## Option C: Claude Code with MCP server

If you've deployed the MCP server, Claude Code can also call it via MCP instead of reading files directly. Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "deepwiki": {
      "url": "https://deepwiki-mcp-{workspace-id}.{cloud}.databricksapps.com"
    }
  }
}
```

## Platform Instructions

### Claude Code

Add to your `CLAUDE.md` (project or global):

```markdown
## DeepWiki Memory

At session start: Read `.deepwiki/workspace/AGENT_PROTOCOL.md` and follow the pre-flight checklist.
At session end: Append to `projects/{project-name}/memory/changelog.md`.
```

### Genie Code / DBSQL Assistant

Copy the contents of `agents/genie_code_instructions.md` into your Genie workspace's Custom Instructions. Replace placeholders with your catalog/schema/volume name.

### GitHub Copilot

Add to `.github/copilot-instructions.md`:

```markdown
At session start, read `.deepwiki/workspace/AGENT_PROTOCOL.md`.
Follow the pre-flight checklist before making any code changes.
```

### Cursor

Add to `.cursorrules`:

```
At session start: Read .deepwiki/workspace/AGENT_PROTOCOL.md.
Before touching any schema: check .deepwiki/projects/{name}/memory/semantic/schemas.md.
After every session that changes anything: append to .deepwiki/projects/{name}/memory/changelog.md.
```

### OpenAI Codex / Custom Agents

Include `AGENT_PROTOCOL.md` in the system prompt. For each task, inject the relevant project slice (schemas, gotchas, changelog) as user context.

## File Ownership

| File | Who edits it |
|------|-------------|
| `NORTH_STAR.md` | Humans only |
| `planning/goals.md`, `planning/phases.md` | Humans only |
| `planning/decisions.md` | Agents propose; humans approve |
| `memory/changelog.md` | Agents write; humans never edit |
| `memory/semantic/*.md` | Agents compile from changelog every 3-5 sessions |
| `workspace/memory/semantic/*.md` | Same; promoted from project-level |
| `context/*.md` | Humans write initially; agents update when infra changes |

## Maintenance

**Every 3-5 sessions:** Ask your agent to run the memory compiler:
> "Compile the last 5 changelog entries into updated semantic memory. Use the template in `agents/delegation_templates/memory_compiler.md`."

**At phase boundaries:** Run the compiler, update `planning/goals.md` and `planning/phases.md`, then start fresh.

**When a gotcha should be promoted to workspace level:** Ask your agent:
> "This gotcha appears in both project-a and project-b. Promote it to `workspace/memory/semantic/gotchas.md`."
