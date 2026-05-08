# External Integrations

> Auth patterns, endpoints, and gotchas for external services.
> Agents check here before writing auth code or making external API calls.

## Databricks CLI

```bash
# Auth via named profile (recommended — no hardcoded tokens)
databricks auth token --profile {profile-name}

# ALWAYS clear env vars to prevent profile override
env -u DATABRICKS_HOST -u DATABRICKS_TOKEN -u DATABRICKS_CONFIG_PROFILE \
  databricks [command] --profile {profile-name}
```

Profiles live in `~/.databrickscfg`. Add new workspaces with `databricks configure --profile {name}`.

## Databricks SDK (Python)

```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient(profile="{profile-name}")
```

## FMAPI (OpenAI-compatible)

```python
from openai import OpenAI
client = OpenAI(
    api_key=w.config.token,
    base_url=f"https://{w.config.host}/serving-endpoints"
)
response = client.chat.completions.create(
    model="databricks-claude-haiku-4-5",
    messages=[{"role": "user", "content": "Hello"}]
)
```

## Google Cloud APIs

```bash
# Use user credentials (NOT application-default — ADC may fail with quota project errors)
TOKEN=$(gcloud auth print-access-token)
curl -H "Authorization: Bearer $TOKEN" https://...
```

## Other Services

| Service | Auth Method | Token Lifetime | Notes |
|---------|------------|---------------|-------|
| *(add yours)* | *(OAuth / API key / etc.)* | *(duration)* | *(gotchas)* |

---

*Add a section for each external service your projects use.*
