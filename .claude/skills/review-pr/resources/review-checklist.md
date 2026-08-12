# Review checklist

What to look for per area. The authority is `.claude/rules/` — this is the reading order,
not a second set of rules. `scripts/review_scope.py` tells you which of these sections
apply to the diff in front of you.

## Read in this order

Schema before the code that queries it, routes before the views that render them, tests
last. Reviewing a view first means re-reading it once you learn the column is nullable.

## Every PR, whatever it touches

- **Does the diff match the description?** Extra work nobody asked for is a finding, even
  when it is good work. It is unreviewable in the same breath as the stated change.
- **Is anything in the diff unexplained by it?** A formatting sweep, a dependency bump, a
  renamed variable in an untouched file — each is a separate PR.
- **Secrets.** No credential, token, or connection string in source. New config comes from
  `.env` and is documented in `.env.example`.
- **Commented-out code, stray `console.log`, a leftover `.only` on a test.**

## Schema and migrations

`.claude/rules/database.md`

- A `schema.ts` change with **no migration** in the same PR will pass lint, pass tests
  against an already-migrated local database, and fail on deploy.
- **Read the generated SQL.** `db:generate` can emit a drop-and-recreate — data loss — from
  an edit that looked purely additive. ESLint ignores `src/db/migrations/`, so a clean lint
  proves nothing here.
- A hand-edited migration is a defect regardless of whether the SQL is correct. The
  workflow is one-way: edit `schema.ts`, regenerate.
- New enum column: `.notNull().default(...)`, or existing rows fail the migration.
- New table: does it declare `relations(...)`? Without it, `with:` queries cannot reach it.
- New child table: `onDelete: "cascade"`, or deleting a parent orphans rows.

## Routes

`.claude/rules/architecture.md`, `.claude/rules/api-style.md`

- **Both surfaces, one commit.** A mutation changed in `app.ts` but not
  `routes/projects.routes.ts` (or the reverse) is the defect this codebase produces most.
  If only one surface should change, the PR should say why.
- Validation is **shared** from `app/src/lib/`, not copied into both handlers. A copied
  check is drift with a delay on it.
- Handlers `throw`; the error middleware formats. An inline `res.status(400).json(...)` is
  a bug even when the response looks identical — it bypasses the single formatting point.
- Order inside a handler: validate input → check the parent exists → write. Tests assert on
  which of 400/404 comes back.
- New JSON routes live under `/api/`. Outside that prefix the error middleware renders HTML
  into a JSON client.
- Status codes: 201 with the created row for a create, 204 empty for a delete, `[]` with
  200 for an empty collection — never 404.
- The response is the row from `.returning()`, not the request body echoed back. Otherwise
  database defaults are missing from the response.

## Views

- A new enum value needs a matching `--<value>` CSS rule, or it renders unstyled — invisible
  in review, visible in production.
- Empty, single, and many. Most view bugs here are a plural label or a missing empty state.
- No client-side framework, no build step. Server-rendered EJS.

## Tests

`.claude/rules/testing.md`

- **A new field needs three cases**: default applied when omitted, valid value accepted,
  invalid value rejected with 400. Two out of three is the usual gap.
- Assert status **and** body. Status alone passes when an error is rendering as HTML.
- The file truncates once in `beforeAll`, so tests share state and order matters. A test
  that asserts on a global count is only correct if nothing before it inserted.
- A new test file needs `afterAll(() => pool.end())` or the run hangs on an open handle.
- Does the test fail if the change is reverted? A test that passes either way is scaffolding,
  not coverage.

## Slides and docs

- Deck number and title must match the `videos` entry in `docs/index.html`.
- Marking an episode `live` means `youtube`, `article` and `slides` all resolve. A live
  entry with a dead link is worse than one still marked upcoming.
- Run `verify_deck.py` on any changed deck — it catches counter, progress-bar and tag
  balance errors that are invisible until the deck is on screen.

## `.claude/` config

- A new entry in `settings.json` `permissions.allow` applies to everyone who clones the
  repo. Read-only commands only; anything that writes, deploys, or spends money should
  stay a prompt.
- A skill's `description` is the whole trigger. If it names the topic but not the phrases
  someone would type, it will not fire.
- New rule files belong in `rules/` only if a change can *violate* them. Descriptive
  explanation goes in `app/CLAUDE.md`.

## Calibration

Three questions before you send a finding:

1. **Can I point at the rule or the breakage?** If not, it is a preference. Say so, or drop it.
2. **Did this PR introduce it?** Run the checker on the base branch too if unsure.
3. **Would I block a merge over it?** If not, it goes under Nits, and the author is free to
   ignore it.

A review of a good PR that says "this is fine, one nit" is a successful review.
