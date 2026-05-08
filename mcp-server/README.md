# DeepWiki MCP Server

FastAPI server that exposes DeepWiki as MCP tools for Genie Code and the Databricks AI Assistant.

## Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `deepwiki_preflight` | Load all session context for a project in one call | `{"project": "my-project"}` |
| `deepwiki_read` | Read a specific file | `{"project": "my-project", "file": "memory/semantic/schemas.md"}` |
| `deepwiki_search` | Full-text search across all files | `{"query": "price model", "max_results": 5}` |
| `deepwiki_changelog` | Append a formatted changelog entry | `{"project": "my-project", "changes": ["Added table X"], "warnings": []}` |
| `deepwiki_list` | List files in a project | `{"project": "my-project"}` or `{}` for project index |

## Setup

### 1. Create a UC Volume for DeepWiki

```sql
CREATE VOLUME {catalog}.{schema}.deepwiki;
```

### 2. Upload the workspace/ and projects/ structure

```bash
# Copy workspace template files to the volume
databricks fs cp -r workspace/ dbfs:/Volumes/{catalog}/{schema}/deepwiki/workspace/

# Create your first project directory
databricks fs mkdirs dbfs:/Volumes/{catalog}/{schema}/deepwiki/projects/my-project/
```

Or use the Databricks UI: Data → Volumes → browse to your volume → Upload.

### 3. Configure the server

Edit `app.yaml` and set `DEEPWIKI_VOLUME` to your volume path:
```yaml
env:
  - name: DEEPWIKI_VOLUME
    value: /Volumes/{catalog}/{schema}/deepwiki
```

### 4. Deploy as a Databricks App

```bash
cd mcp-server/
databricks apps deploy deepwiki-mcp --source-code-path .
```

### 5. Register as MCP Server in Genie Code

After deploying, add to `.assistant/.mcp_servers.json` in your workspace:
```json
{
  "name": "DeepWiki",
  "url": "https://deepwiki-mcp-{workspace-id}.{cloud}.databricksapps.com",
  "isToggledOn": true,
  "disabledTools": [],
  "mcpType": "custom"
}
```

## Local Testing

```bash
pip install -r requirements.txt

# Point at a local directory instead of a UC Volume
DEEPWIKI_VOLUME=/path/to/your/local/deepwiki python deepwiki_mcp.py

# Test it
curl http://localhost:8100/health
curl -X POST http://localhost:8100/tools/deepwiki_list \
  -H "Content-Type: application/json" \
  -d '{}'
```

## How Genie Code Uses It

Once registered, Genie can call these tools naturally:

```
User: "Start a new session on my-project"
Genie: [calls deepwiki_preflight(project="my-project")]
       → Returns protocol + gotchas + schemas + recent changelog
```

```
User: "I just added a new column to events table"  
Genie: [calls deepwiki_changelog(project="my-project",
         changes=["Added column user_id to gold.events"],
         schema_changes=["gold.events: added user_id (STRING)"])]
       → Appends formatted entry
```
