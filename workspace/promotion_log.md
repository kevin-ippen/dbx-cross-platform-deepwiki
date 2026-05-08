# Promotion Log

> Append-only record of what was promoted from project-level to workspace-level memory.
> Agents log here whenever promoting a gotcha, pattern, term, or schema entry.

## Format

```
## YYYY-MM-DD | {From Project} → Workspace | {Category}

- **What:** *(what was promoted — exact entry or summary)*
- **Why:** *(why it's workspace-general, not project-specific)*
- **From file:** `projects/{name}/memory/semantic/{file}.md`
- **Into file:** `workspace/memory/semantic/{file}.md`
```

---

*(No promotions yet — this log fills in as you bootstrap projects and run harmonization.)*
