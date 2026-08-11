# Rules: JSON API style

Applies to routes under `/api/*` in `app/src/routes/`. The structural split between this
surface and the HTML one is covered in [architecture.md](architecture.md); this file is the
HTTP contract every `/api/*` endpoint must honour.

## Paths

- Plural resource nouns, kebab-case if multi-word: `/api/projects`, not `/api/project`.
- Nested resources carry the full parent chain:
  `/api/projects/:projectId/tasks/:id`. When a route has two ids, name the parent
  explicitly (`:projectId`), never two bare `:id`s.
- Never encode the verb in the path. `DELETE /api/projects/:id`, not
  `POST /api/projects/:id/delete` — that form exists only on the HTML surface, because
  browser forms cannot issue DELETE.
- Every path starts with `/api/`. The error middleware in `app.ts` switches on
  `req.path.startsWith("/api")`, so a JSON route outside that prefix renders an HTML error
  page on failure.

## Status codes

| Situation | Status | Body |
|---|---|---|
| Read succeeded | 200 | the resource, or `[]` for an empty collection |
| Resource created | 201 | the created row, from `.returning()` |
| Deleted | 204 | none — `res.status(204).send()` |
| Input invalid or missing | 400 | `{ "error": "…" }` via `ValidationError` |
| Resource does not exist | 404 | `{ "error": "…" }` via `NotFoundError` |
| Anything unhandled | 500 | `{ "error": "…" }` |

An empty collection is `200` with `[]`, never `404`.

## Response bodies

- Success bodies are the raw Drizzle row (or array of rows) — no envelope, no
  `{ data: … }` wrapper. Nested children come from `with:`, so
  `GET /api/projects/:id` returns the project with a `tasks` array on it.
- Return the row the database produced, via `.returning()` — never echo back the request
  body. Defaults applied by Postgres (`status`, `priority`, `createdAt`) must appear in the
  response.
- Error bodies are exactly `{ "error": "<message>" }`. That shape is produced in one place,
  the error middleware in `app.ts`. Do not construct an error response in a handler.

## Request handling order

Inside a handler, in this order:

1. **Validate input** — `ValidationError` (400) for a missing or malformed field. Shared
   parsers from `src/lib/` do this; call them before touching the database.
2. **Check the parent exists** — `NotFoundError` (404).
3. **Perform the write**, then respond.

The order is deliberate: bad input on a nonexistent parent returns 400, not 404. Keep it
consistent, since tests assert on the specific code.

## Errors

Handlers `throw`; they never format a response. Wrap the body in `try/catch` and forward
with `next(err)`. Adding a `res.status(4xx).json(...)` inside a handler is a bug even when
the output looks identical — it bypasses the single formatting point.

## Authentication

`/api/*` is currently unauthenticated by design; see the security note in
[`../specs/01-login-logout.md`](../specs/01-login-logout.md). Any spec that changes this
must state what happens to the existing tests, which call the API with no credentials.
