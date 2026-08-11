# Route contract — what each finding means and how to fix it

One section per rule emitted by `scripts/audit_routes.py`. The authority for all of this is
`.claude/rules/architecture.md` and `.claude/rules/api-style.md`; this file is the fix
recipe, not a second set of rules.

## `architecture/dual-surface`

The two surfaces disagree about the same operation.

**Validation drift.** The `/api` handler validates, its HTML twin does not. Real example:
`POST /api/projects` throws `ValidationError` when `name` is missing, while `POST /projects`
inserts whatever the form sent — so an empty name creates a project with a blank title,
because `text().notNull()` accepts `""`.

Fix by sharing the check, never by copying it. Put the parser in `app/src/lib/`, have it
throw `ValidationError` itself, and import it on both surfaces. `task-priority.ts` is the
reference:

```ts
export const TASK_PRIORITIES = taskPriority.enumValues;   // derived from the pgEnum

export function parsePriority(value: unknown): TaskPriority | undefined {
  if (value === undefined || value === "") return undefined;
  if (typeof value !== "string" || !TASK_PRIORITIES.includes(value as TaskPriority)) {
    throw new ValidationError(`priority must be one of ${TASK_PRIORITIES.join(", ")}`);
  }
  return value as TaskPriority;
}
```

Two properties matter. It returns `undefined` for absent input so callers can spread it
conditionally — `...(priority && { priority })` — and let the database default apply. And it
derives its allowed values from the enum instead of repeating the list.

**Missing existence check.** `POST /projects/:id/tasks` inserts without confirming the
project exists, so a bad id becomes a foreign-key violation: a 500 rendering the raw
Postgres message into `error.ejs`. Query the parent first and throw `NotFoundError`.

Order is fixed by `api-style.md`: validate input, then check the parent, then write. Bad
input on a nonexistent parent returns 400, not 404, and tests assert on that.

**No equivalent on the other surface.** Not automatically a defect. Ask whether the
operation belongs on both. Most mutations do; browser-only flows like login do not.

## `architecture/error-handling`

**Inline error response.** A handler calling `res.status(404).render(...)` or
`res.status(400).json(...)` bypasses the single error middleware at the bottom of
`app/src/app.ts`, which is the only place allowed to format an error. It is a bug even when
the output looks identical, because it is the point where the two surfaces start to diverge.

```ts
// wrong
if (!project) {
  res.status(404).render("error", { message: "Project not found" });
  return;
}

// right
if (!project) throw new NotFoundError("Project not found");
```

The middleware picks the format from `req.path.startsWith("/api")`, so one throw serves
both surfaces correctly.

The deliberate exception is `POST /login` in `auth.routes.ts`, which re-renders its own form
with an inline message because a rejected login is expected user flow, not an error. Leave
it alone.

**Async handler with no try/catch.** Express 4 does not catch rejected promises, so the
request hangs until it times out and the error middleware never runs. Wrap the body and
forward with `next(err)`.

## `validation/ids`

`Number(req.params.id)` returns `NaN` for a non-numeric id, and `NaN` goes straight into
`eq(projects.id, NaN)`. The result is a database error surfaced as a 500 with Postgres
internals in the body — on the JSON surface that is an information leak, on the HTML
surface it is a broken page.

There is no id parser in `app/src/lib/` yet. Add one next to the other parsers:

```ts
export function parseId(value: unknown): number {
  const id = Number(value);
  if (!Number.isInteger(id) || id < 1) throw new ValidationError("id must be a positive integer");
  return id;
}
```

Then replace every `Number(req.params.x)` with `parseId(req.params.x)` — the audit reports
each site. Do all of them or none; half-converted is worse than consistent.

Note the consequence before doing it: `/api/projects/abc` changes from 500 to 400. That is
the correct code, but it is a behaviour change worth stating.

## `auth/guards`

Mutating HTML routes are guarded by `requireAuth`
(`app/src/middleware/require-auth.ts`), which redirects anonymous visitors to `/login`. A
new mutating HTML route without it is a hole.

`/api/*` is unauthenticated on purpose — see `.claude/specs/01-login-logout.md`, scope
boundary 2 — so the audit does not flag API routes. Do not "fix" that here. Closing it
changes every existing API test, which currently sends no credentials, and needs a spec.

## `architecture/shared-code`

A helper defined in more than one route file. `byPriorityThenCreatedAt` is the live case:
identical copies in `app.ts` and `projects.routes.ts`, each carrying its own
`eslint-disable-next-line` for the sanctioned `any`. Task ordering therefore cannot be
changed in one place.

Move it to `app/src/lib/task-order.ts`, export it, import it in both. Keep the
`eslint-disable` comment with the code — `code-style.md` allows that one `any` only when it
is explicitly disabled and explained.

## Checks the script cannot make

Do these by eye when the audit is part of a review:

- Response bodies are raw Drizzle rows from `.returning()` — no `{ data: ... }` envelope,
  and never an echo of the request body, or Postgres defaults will be missing from the
  response.
- An empty collection is `200` with `[]`, never `404`.
- Deletes scoped to a parent filter on both ids —
  `and(eq(tasks.id, id), eq(tasks.projectId, projectId))` — so a task cannot be deleted
  through the wrong project.
- New enum values are not duplicated between `schema.ts`, a route and a view.
