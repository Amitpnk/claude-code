# Rules: architecture

Enforceable constraints for `app/`. The descriptive overview lives in
[app/CLAUDE.md](../../app/CLAUDE.md) — this file is the checklist that changes are held to.

## Dual route surface

Every resource operation has up to two homes. They are not interchangeable:

| Surface | File | Input | Success | Failure |
|---|---|---|---|---|
| HTML | `app/src/app.ts` | form body (`express.urlencoded`) | `res.redirect(...)` | rendered `error.ejs` |
| JSON | `app/src/routes/projects.routes.ts` (`/api/*`) | JSON body | `res.json` / `res.status(201)` / `204` | JSON `{ error }` |

- Before adding an operation, state explicitly which surfaces it belongs on and why.
  Most mutations belong on both.
- When changing behaviour for a resource, change **both** surfaces in the same edit.
  The two surfaces drifting apart is this codebase's most common defect.
- `projectsRouter` is mounted in `app.ts` before the HTML routes. Keep API paths under
  `/api/` — the error middleware uses `req.path.startsWith("/api")` to pick its format,
  so an API route outside `/api/` silently renders HTML on error.

### Known drift — do not copy these as patterns

These exist today and are wrong under the rules above. Fix them if you touch the route,
don't imitate them elsewhere:

- `app.ts` `GET /projects/:id` handles 404 inline with `res.status(404).render(...)`
  instead of throwing `NotFoundError`.
- `app.ts` `POST /projects` and `POST /projects/:id/tasks` skip the `name`/`title`
  validation and the parent-exists check that their `/api/*` twins perform.

## Error handling

- Handlers **throw** an `AppError` subclass from `app/src/lib/errors.ts`
  (`NotFoundError` → 404, `ValidationError` → 400).
- Every async handler wraps its body in `try/catch` and forwards with `next(err)`.
  Never `res.status(...)` an error inline.
- The single error middleware at the bottom of `app/src/app.ts` is the only place that
  formats an error response. Do not add a second error handler.
- Non-`AppError` throws become 500 with their raw message. If a failure has a meaningful
  status, give it an `AppError` subclass rather than letting it fall through.

## Shared validation

- Validation that both surfaces need lives in `app/src/lib/`, is imported by both, and
  throws `ValidationError` itself. `parsePriority` in `task-priority.ts` is the reference
  implementation: it derives its allowed values from the pgEnum
  (`taskPriority.enumValues`) rather than repeating the list.
- A validator returns `undefined` for absent input (`undefined` or `""`) so callers can
  spread it conditionally — `...(priority && { priority })` — and let the DB default apply.
- Never duplicate an allowed-values list between `schema.ts`, a route, and a view.
  Derive it from the enum.

## TypeScript

- Strict mode. No `any` and no non-null assertions used to silence the compiler.
- The one sanctioned `any` is the `byPriorityThenCreatedAt` Drizzle order-by callback,
  which carries an `eslint-disable-next-line` and is duplicated in `app.ts` and
  `projects.routes.ts`. If you touch task ordering, change both copies.

## Views

- All templates use the existing `partials/header` and `partials/footer`.
- Enum-valued fields render as `<span class="<field>-badge <field>-badge--<value>">`,
  with matching CSS in `app/src/public/styles.css`. Follow the existing badge pattern
  rather than inventing new markup.
- Server-rendered EJS only. Do not introduce a client-side framework or a build step
  for the views.

## Configuration

No secrets in source. New config is read from `.env` and documented in `.env.example`.
