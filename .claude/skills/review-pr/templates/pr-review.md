# Review — <PR #N or branch> — <date>

<One sentence: what the change does, in your words, not the description's. If you
cannot state it in one sentence, that is the first finding.>

Checked against: <rules files that applied>.
Ran: <checkers, lint, tests — or "read the code only; Postgres was not up">.

## Blocking

<Merging this breaks something a user can hit, loses data, or leaks internals.
Empty this section when there is nothing in it — do not pad it.>

- **A non-numeric project id returns 500 with a raw Postgres message.**
  `Number(req.params.id)` yields `NaN` and reaches the query. Parse the id through a
  `parseId` in `src/lib/` and throw `ValidationError`.
  `app/src/routes/projects.routes.ts:43`

## Should fix before merge

<Real defects that are not emergencies. Drift between the surfaces, missing test
cases, a seed that leaves a new branch unreachable.>

- **`POST /projects` accepts the new field without validating it; the API twin does.**
  The two surfaces will disagree the first time someone posts the form. Import the same
  `parseDueDate` on both. `app/src/app.ts:60` vs `projects.routes.ts:28`

## Questions

<Things that look wrong but may be deliberate. Ask; do not assert. A one-surface
operation, a deliberately skipped check, anything where the fix changes documented
behaviour.>

- The HTML delete does not 404 on a missing row, the API does. Deliberate for a form
  surface? If so it is worth a comment at `app/src/app.ts:88`.

## Nits

<Naming, duplication, formatting the linter does not catch. Label them as optional so
the author can skip them without guilt.>

- `byPriorityThenCreatedAt` is now duplicated a third time — `app.ts:15`,
  `projects.routes.ts:9`, `tasks.routes.ts:11`. Worth extracting, not in this PR.

## Pre-existing — not from this PR

<Anything the checkers reported that the diff did not introduce. Keeping it separate is
what makes the sections above trustworthy.>

- `audit_routes.py` returns 17 findings on `main` as well; 14 are unrelated to these files.

## Verdict

<One of: ready to merge / ready once the blocking items are fixed / needs a
conversation about approach. Then the shortest path to green.>

Ready once the id parsing is fixed. Everything else can follow in a separate PR.
