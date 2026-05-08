# Cross-Project References

> Which projects own which assets, and who consumes them.
> Agents check this before modifying a shared schema or asset.

## Ownership Map

| Asset | Type | Owner | Consumers | Notes |
|-------|------|-------|-----------|-------|
| *(table or endpoint name)* | Delta table | *(owner project)* | *(consumer projects)* | *(any schema or timing constraints)* |

## Dependency Graph

```
*(sketch your dependency graph here once you have multiple projects)*

Example:
  project-a (writes gold_metrics)
       ↓
  project-b (reads gold_metrics, writes gold_forecasts)
       ↓
  project-c (reads gold_forecasts)
```

## Rules for Cross-Project Changes

1. **Before modifying a shared asset**: check the Consumers column above
2. **Notify downstream**: add a warning in your changelog entry under "Warnings for Next Session"
3. **Coordinate schema changes**: open an entry in `planning/open_questions.md` in the consumer project
4. **Never write to another project's `.deepwiki/`**: you are a guest; leave notes in your own project's `open_questions.md`

---

*Add a row whenever a table or model endpoint is consumed by more than one project.*
