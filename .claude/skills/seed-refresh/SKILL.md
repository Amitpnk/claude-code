---
name: seed-refresh
description: Check and extend TaskFlow's sample data in app/src/db/seed.ts so it exercises every enum value, every optional column, and every collection shape the views branch on. Use for requests like "check the seed", "does the seed cover everything", "refresh the sample data", or "add seed data" - and after adding a column, adding an enum value, or changing a view that branches on data.
---

# Keeping the seed honest

`app/src/db/seed.ts` is the only data most people ever look at while developing. Anything it
never produces is a view branch nobody sees — not in the browser, not in a screenshot. The
checker finds those blind spots:

```bash
python .claude/skills/seed-refresh/scripts/check_seed.py
```

Exit 0 is clean, 1 means gaps. It prints an `ok` line for each check that passed, so a clean
run still shows its work.

## What it checks

1. **Enum coverage** — every `pgEnum` value appears in the seed.
2. **Optional columns** — a nullable column that every seeded row sets, so the empty case never
   renders.
3. **Collection shapes** — a project with zero tasks, and one with exactly one.
4. **Badge styles** — every enum value has a matching `--<value>` rule in `styles.css`.

`resources/seed-coverage.md` explains why each one matters and which view branch it maps to.
Read it before editing the seed.

## Verify before reporting

**The script reads TypeScript as text.** Open the line it cites before acting on a finding. It
cannot see anything computed at runtime, and an unusual seed layout can mislead it — check 3 in
particular only understands the current `const [a, b] = await db.insert(projects)` shape.

A finding is a question about coverage, not a defect. Say what is uncovered and which branch
that hides; do not describe the seed as broken.

## Fixing a gap

Edit `app/src/db/seed.ts` using `templates/seed-block.md` as the shape. Two rules that matter
more than they look:

- **Omit an optional key rather than passing `null`.** Omitting lets the database default apply,
  which is the path a row created through the UI takes.
- **Put mixed priorities inside one project.** Ordering is applied per project, so priorities
  spread across several projects prove nothing about sorting.

Re-run the checker until it is clean.

## Running the seed — ask first

`npm run db:seed` **destroys and rewrites local data, and is not idempotent**: it uses plain
inserts, and `users.email` is unique, so a second run fails on a duplicate key. It has to be
preceded by a TRUNCATE. The exact commands are in `resources/seed-coverage.md`.

Never run it unprompted. Someone's local database may hold work they care about. Change the
file, show the checker passing, and let the user decide when to apply it.

Running it needs `docker compose up -d`. If Postgres is not up, say the changes are unverified
against a real database rather than implying they were applied.
