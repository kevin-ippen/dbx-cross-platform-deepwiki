# DAB Manifest

> Databricks Asset Bundle structure and deployment state.
> Agent reads this when deploying, running jobs, or modifying bundle resources.
> Populated during bootstrap (see BOOTSTRAP.md Prompt 3).

## Bundle Root

```yaml
# Summary of databricks.yml
bundle:
  name: *(your-bundle-name)*

targets:
  dev:
    workspace:
      host: *(dev workspace URL)*
  prod:
    workspace:
      host: *(prod workspace URL)*
```

## Resources

| Resource | Type | Name in Bundle | Deployed State |
|----------|------|---------------|----------------|
| *(e.g. ingest job)* | job | *(ingest_pipeline)* | *(deployed / not deployed)* |
| *(e.g. my app)* | app | *(my-app)* | *(deployed / not deployed)* |

## Jobs

| Job | Schedule | Cluster Config | Last Run Status |
|-----|----------|---------------|-----------------|
| *(job name)* | *(cron / manual)* | *(serverless / cluster policy)* | *(succeeded / failed / unknown)* |

## Variables

| Variable | Dev Value | Prod Value | Purpose |
|----------|-----------|------------|---------|
| `catalog` | *(dev catalog)* | *(prod catalog)* | *(target catalog for all tables)* |

## Deployment Notes

*(Anything an agent needs to know before running `bundle deploy` — e.g., required manual steps, known issues.)*

---

*Run `databricks bundle validate` before every `bundle deploy`.*
*Run `bundle deploy --var key=value` before `bundle run` to rebake job parameters.*
