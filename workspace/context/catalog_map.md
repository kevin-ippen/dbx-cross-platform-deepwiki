# Catalog Map

> Full topology of Unity Catalog: catalogs, schemas, and what lives in each.
> Agents check here before assuming a schema exists.

## How to Read This

```
{catalog}
  └── {schema}        ← what it holds (owner project)
        ├── {table}   ← brief description
        └── {table}
```

---

## {your_catalog}

*(Replace with your actual catalog structure. Example below:)*

```
my_catalog
  └── bronze_events      ← raw ingested events (project: my-project)
        ├── raw_clickstream
        └── raw_transactions
  └── silver_events      ← cleaned and joined (project: my-project)
        ├── enriched_sessions
        └── user_activity
  └── gold_metrics       ← business-ready aggregates (project: my-project)
        └── daily_kpis
```

---

*Add catalogs and schemas as you create them. This is the source of truth agents use to avoid creating duplicate schemas.*
