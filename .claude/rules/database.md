# Rules: database

Applies to `app/src/db/`. Read alongside [architecture.md](architecture.md).

## Source of truth

`app/src/db/schema.ts` is the only place schema is authored. The workflow is one-way:

```
edit schema.ts  →  npm run db:generate  →  review the SQL  →  npm run db:migrate
```

- **Never hand-edit a file under `src/db/migrations/`.** To change a migration that has
  not shipped, revert it, change `schema.ts`, and regenerate.
- Always read the generated SQL before applying it. `db:generate` can emit a destructive
  plan (a column drop/recreate that loses data) from an edit that looked additive.
- Migrations are excluded from ESLint (`eslint.config.js` ignores `src/db/migrations/**`),
  so lint passing says nothing about whether a migration is correct.

## Schema conventions

- Fixed-value fields are Postgres enums declared with `pgEnum`, named `snake_case` in the
  DB and `camelCase` in TS — see `taskStatus` (`task_status`) and `taskPriority`
  (`task_priority`).
- Enum columns are `.notNull().default(...)` so existing rows survive the migration and
  routes can omit the field. `tasks.status` defaults to `todo`, `tasks.priority` to
  `medium`.
- Child rows use `.references(() => parent.id, { onDelete: "cascade" })`. `tasks` cascade
  from `projects`; deleting a project must not orphan tasks.
- Every table declares its `relations(...)` block so `db.query.<table>.findMany({ with: … })`
  works. A new table without relations will not be reachable from a nested query.
- Timestamps are `timestamp("created_at").notNull().defaultNow()`.

## Queries

- Drizzle only. No raw SQL in route handlers — the one exception is the
  tagged-template `sql` priority-ordering CASE expression, which Drizzle cannot
  express natively.
- Prefer `db.query.<table>.findFirst/findMany` with `with:` over manual joins.
- Deletes scoped to a parent must filter on both ids —
  `and(eq(tasks.id, id), eq(tasks.projectId, projectId))` — so a task cannot be deleted
  through the wrong project.

## Seeds

`src/db/seed.ts` must exercise more than one value of every enum column. A seed where
every task is `medium`/`todo` hides badge-rendering and ordering bugs.
