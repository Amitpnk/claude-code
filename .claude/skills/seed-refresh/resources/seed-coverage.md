# What the seed has to cover, and how to run it safely

`.claude/rules/database.md` states the rule this skill enforces:

> `src/db/seed.ts` must exercise more than one value of every enum column. A seed where every
> task is `medium`/`todo` hides badge-rendering and ordering bugs.

That is the floor, not the whole story. The seed is the only data most people ever look at
while developing, so **anything the seed never produces is a view branch nobody sees** — not in
the browser, not in a screenshot, not on camera. Bugs live there.

## The four checks

### 1. Enum coverage

Every value of every `pgEnum` must appear at least once. Missing values mean an unexercised
badge and, for `task_priority`, an unexercised branch of the ordering CASE expression that
`byPriorityThenCreatedAt` builds.

Mixed priorities need to sit **inside one project**, not spread across several. Ordering is
applied per project via `with: { tasks: { orderBy: ... } }`, so a project whose tasks are all
`high` proves nothing about sorting.

### 2. Optional columns

A column without `.notNull()` can be absent, and the views branch on that. `projects.description`
is the live case: `dashboard.ejs:17` and `project.ejs:8` both wrap it in `<% if (...) %>`, and
with today's seed the falsy side never renders.

Prefer **omitting the key** over passing `null`. Omitting lets the database default apply, which
is the path a row created through the UI takes; passing `null` explicitly tests a path the app
never produces.

### 3. Collection shapes

Parent rows need varied child counts — at least one with **zero** children and one with
**exactly one**:

- Zero exercises the empty `.task-list` state in `project.ejs`.
- Exactly one exercises `dashboard.ejs:21`, which picks `task` vs `tasks` on `length === 1`.

With every project holding two or more tasks, both labels are permanently wrong-by-omission.

### 4. Badge styles

Each enum value renders as `<span class="<field>-badge <field>-badge--<value>">`, and each needs
a matching rule in `app/src/public/styles.css`. A value with no rule renders as unstyled text
next to properly styled siblings — obvious on screen, invisible in a passing test suite.

Adding an enum value therefore touches three places: `schema.ts`, `styles.css`, and `seed.ts`.
The script checks all three are in step.

## Running the seed

**`npm run db:seed` is not idempotent.** It does plain inserts with no `onConflictDoNothing`,
and `users.email` is `.unique()` (`schema.ts:47`), so a second run fails on a duplicate key
before it inserts anything else. There is no `db:reset` script in `package.json`.

Reset first, using the same statement the tests use in `beforeAll`:

```bash
docker compose up -d
docker compose exec -T postgres psql -U postgres -d taskflow \
  -c "TRUNCATE TABLE tasks, projects, sessions, users RESTART IDENTITY CASCADE;"
npm run db:seed
```

`RESTART IDENTITY` matters: without it, ids keep climbing and the seeded projects stop being
`/projects/1` and `/projects/2`, which breaks any bookmark, screenshot or recorded demo that
points at a specific id.

Truncating `sessions` logs everyone out. That is correct — a session row referencing a deleted
user is worse.

## The relationship with tests

From `.claude/rules/testing.md`: both test files truncate `tasks, projects, sessions, users` in
`beforeAll`. So:

- Running `npm run test` **destroys local seed data**. Re-seed afterwards.
- The reverse is safe — seeding does not disturb tests, since they truncate before running.
- Never make the test suite depend on seeded rows. Tests create the rows they need.

## Adding a new table

When a table is added to `schema.ts`, the seed needs a block for it before this checker can say
anything useful about it. Give the new block the same properties:

- every enum value used at least once,
- at least one row omitting each optional column,
- if it has children, a parent with none and a parent with exactly one,
- a `.returning()` destructure if later inserts need its ids.

Insert parents before children — the foreign keys are `.notNull()`, so order is not optional.
