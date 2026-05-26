# DeepWiki MCP Server

MCP server that exposes DeepWiki as tools for Genie Code and the Databricks AI Assistant. Uses the MCP Python SDK with Streamable HTTP transport — Genie Code can discover and invoke tools via JSON-RPC without any custom configuration.

## Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `deepwiki_preflight` | Load session context for a project, including recent episodic logs | `{"project": "my-project"}` |
| `deepwiki_resolve_project` | Fuzzy-resolve project names before creating/selecting memory | `{"project": "my proj"}` |
| `deepwiki_read` | Read a specific file | `{"project": "my-project", "file": "memory/semantic/schemas.md"}` |
| `deepwiki_search` | Full-text search across all files | `{"query": "price model"}` |
| `deepwiki_checkpoint` | Append an in-flight episodic event | `{"project": "my-project", "summary": "validated schema", "status": ["DESCRIBE matched"]}` |
| `deepwiki_episodic` | Alias for appending an episodic event | `{"project": "my-project", "summary": "plan revised", "event_type": "Plan"}` |
| `deepwiki_changelog` | Append a formatted changelog entry | `{"project": "my-project", "changes": ["Added table X"]}` |
| `deepwiki_close_session` | Append final episodic close event and changelog together | `{"project": "my-project", "summary": "finished task", "changes": ["..."]}` |
| `deepwiki_list` | List files in a project | `{"project": "my-project"}` or `{}` for project index |

Read tools may fuzzy-resolve a project name to help with discovery. Write tools (`deepwiki_checkpoint`, `deepwiki_episodic`, `deepwiki_changelog`, and `deepwiki_close_session`) fail closed unless the supplied project name resolves exactly; call `deepwiki_resolve_project` first and retry with the exact name when a name is approximate.

## Setup

### 1. Create a UC Volume for DeepWiki

```sql
CREATE VOLUME {catalog}.{schema}.deepwiki;
```

### 2. Upload the workspace/ and projects/ structure

```bash
databricks fs cp -r workspace/ /Volumes/{catalog}/{schema}/deepwiki/workspace/ --recursive
databricks fs cp -r projects/_template/ /Volumes/{catalog}/{schema}/deepwiki/projects/my-project/ --recursive
```

Or use the Databricks UI: Data → Volumes → browse to your volume → Upload.

Grant your app's service principal `READ VOLUME` and `WRITE VOLUME` on the volume (UC grants, not app resources).

### 3. Configure the server

Edit `app.yaml` and set `DEEPWIKI_VOLUME` to your volume path:
```yaml
env:
  - name: DEEPWIKI_VOLUME
    value: /Volumes/{catalog}/{schema}/deepwiki
```

### 4. Deploy as a Databricks App

The app name **must start with `mcp-`** — Genie Code uses this prefix to identify MCP servers.

```bash
cd mcp-server/
databricks apps deploy mcp-deepwiki --source-code-path .
```

### 5. Register in Genie Code

1. Open Genie Code settings
2. Navigate to **MCP Servers**
3. Click **Add MCP Server** → select **Databricks App**
4. Choose `mcp-deepwiki` from the app list

Genie Code will auto-discover all tools at the `/mcp` endpoint.

## Local Testing

```bash
pip install -r requirements.txt

# Point at a local directory instead of a UC Volume
DEEPWIKI_VOLUME=/path/to/your/local/.deepwiki uvicorn deepwiki_mcp:app --port 8100

# Send a JSON-RPC initialize request
curl -X POST http://localhost:8100/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}'
```

## How Genie Code Uses It

Once registered, Genie can call these tools naturally:

```
User: "Start a new session on my-project"
Genie: [calls deepwiki_preflight(project="my-project")]
       → Returns protocol + gotchas + schemas + recent changelog + recent episodic logs
```

```
User: "I just added a new column to events table"
Genie: [calls deepwiki_changelog(project="my-project",
         changes=["Added column user_id to gold.events"],
         schema_changes=["gold.events: added user_id (STRING)"])]
       → Appends formatted entry
```
