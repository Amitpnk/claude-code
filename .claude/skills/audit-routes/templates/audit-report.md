# Route audit — <date>

Ran `audit_routes.py` (<N> findings) and verified each against the source.
Test suite: <ran clean / not run, Postgres was not up>.

## Breaks for a user

<Findings where a request returns the wrong thing, leaks internals, or corrupts data.
One bullet each: what happens, then the fix, then the location.>

- **A non-numeric id returns 500 with a Postgres message.** `Number(req.params.id)` yields
  `NaN`, which reaches the query. Add `parseId` in `src/lib/` and use it at all 10 sites.
  `app/src/app.ts:73`, `app/src/routes/projects.routes.ts:43`, +8 more.

## Drift between the surfaces

<Where HTML and /api disagree. Say which surface is correct and which moves.>

- **`POST /projects` accepts a blank name; `POST /api/projects` rejects it.** The API is
  correct. Extract a `parseName` into `src/lib/` and call it from both.
  `app/src/app.ts:60` vs `app/src/routes/projects.routes.ts:28`.

## Needs a decision

<Findings that are questions, not defects: one-surface operations, deliberate scope gaps,
anything where the fix changes documented behaviour. Do not fix these unprompted.>

- **HTML deletes do not 404 on a missing row, the API does.** Arguably right for a form
  surface. Confirm before aligning.

## Cosmetic

<Duplication, naming, structure. Real but nothing observable changes.>

- **`byPriorityThenCreatedAt` is duplicated** in `app.ts:15` and
  `projects.routes.ts:9`. Move to `src/lib/task-order.ts`.

## Recommended order

1. <the cheapest fix that removes a user-visible failure>
2. <the rest, grouped so each step ends with lint and tests clean>

Not fixed: <anything listed above and deliberately left, with the reason.>
