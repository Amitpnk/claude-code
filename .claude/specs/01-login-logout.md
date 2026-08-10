# Spec: Login and Logout

## Problem statement

TaskFlow has no concept of a user. Every visitor to `http://localhost:3000` sees the same
dashboard and can create or delete any project or task anonymously — there is no `users` table in
`src/db/schema.ts`, no session middleware in `src/app.ts`, and nothing in `partials/header.ejs`
that reflects who is using the app. This feature introduces the first identity layer: a login page
that authenticates a seeded user against a hashed password, a server-side session that survives
across requests, a logout action that ends it, and a `requireAuth` guard on the HTML routes that
mutate data. It is the prerequisite for anything later that needs to know *who* did something —
per-user projects, assignees, audit trails.

## Depends on

No dependencies. This is the first spec in `.claude/specs/`.

## Scope boundaries

Three deliberate exclusions, each with its reason. Read these before planning — they define what
"done" does *not* include.

1. **No registration / signup UI.** The title of this feature is login *and logout*. Users are
   created by `npm run db:seed` only. A self-service registration page is a separate spec
   (`02-registration`), and building it here would double the surface area of this one.
2. **The JSON API under `/api/*` stays unauthenticated.** Gating it would break all 14 existing
   tests in `tests/projects.test.ts`, which call the API with no credentials. Keeping the API open
   lets this spec land with the suite green.
   > **Security note — read this.** For the duration of this spec, `/api/*` is an unauthenticated
   > bypass of the UI's auth: anyone who can reach the server can `DELETE /api/projects/1`
   > regardless of login state. That is acceptable only because TaskFlow is a local demo app bound
   > to localhost. Securing the API surface is a required follow-up (`03-api-authentication`) and
   > must happen before this app is exposed anywhere beyond a developer's machine.
3. **Password reset, "remember me", email verification, rate limiting, and account lockout are out
   of scope.** Each is a separate concern with its own spec.

## Functional requirements

1. A `users` table exists with a unique email and a hashed password — never a plaintext one.
2. `npm run db:seed` creates at least two users with known credentials, so the login page is
   usable immediately after a fresh setup.
3. `GET /login` renders a login page with email and password fields.
4. `POST /login` with a correct email and password establishes a session and redirects to `/`.
5. `POST /login` with an unknown email OR an incorrect password re-renders the login page with a
   single generic error message and does not reveal which of the two was wrong.
6. `POST /login` with a missing email or missing password re-renders the login page with a
   validation message, without querying the database for a user.
7. A logged-in user's session survives across subsequent requests until logout or expiry.
8. `POST /logout` destroys the session, clears the session cookie, and redirects to `/login`.
9. The header shows the signed-in user's email and a Logout button when a session exists, and a
   Login link when it does not.
10. The HTML routes that mutate data (`POST /projects`, `POST /projects/:id/delete`,
    `POST /projects/:id/tasks`, `POST /projects/:projectId/tasks/:id/delete`) reject unauthenticated
    requests by redirecting to `/login`.
11. The HTML read routes (`GET /`, `GET /projects/:id`, `GET /about`, `GET /terms`, `GET /privacy`)
    remain publicly readable.
12. A visitor who is already logged in and requests `GET /login` is redirected to `/` rather than
    shown the form again.
13. Session records are stored in Postgres, not in memory, so they survive a dev-server restart.

## Routes

**HTML (form-post, rendered EJS — new `src/routes/auth.routes.ts`, mounted in `src/app.ts`)**

- `GET /login` — render the login form — public (redirects to `/` if already authenticated)
- `POST /login` — authenticate credentials, establish session, redirect to `/` — public
- `POST /logout` — destroy session, redirect to `/login` — authenticated

**JSON API (`/api/*`)**

No new routes. Per scope boundary 2, authentication is not exposed on the JSON surface in this
spec. This is the one place where the "keep both surfaces in sync" rule in
`.claude/rules/architecture.md` is deliberately not applied, because a JSON login endpoint without
API-wide auth enforcement would be a half-built surface. `04-api-authentication` covers it properly.

**Changed behaviour on existing HTML routes** — the four mutating routes listed in functional
requirement 10 gain the `requireAuth` middleware. Their success behaviour is unchanged.

## API contracts

No JSON endpoints are added. The HTML form contracts are:

**`POST /login`**
- Request: `application/x-www-form-urlencoded`
  - `email` — string, required, trimmed and lowercased before lookup
  - `password` — string, required, compared as given (never trimmed — leading/trailing whitespace
    is significant in a password)
- Success: `302` redirect to `/`, `Set-Cookie` with the session id
- Failure (bad credentials): `401`, renders `login.ejs` with
  `{ error: "Invalid email or password", email: <the submitted email> }` — the password field is
  never echoed back
- Failure (missing field): `400`, renders `login.ejs` with
  `{ error: "Email and password are required", email: <the submitted email or ""> }`

**`POST /logout`**
- Request: no body
- Success: `302` redirect to `/login`, session destroyed and cookie cleared
- Unauthenticated: `302` redirect to `/login` (idempotent — logging out when not logged in is not
  an error)

## Database changes

Two new tables in `src/db/schema.ts`. Verified against the current schema, which contains only
`projects` and `tasks` and the `task_status` / `task_priority` pgEnums.

**`users`**
| Column | Type | Notes |
|---|---|---|
| `id` | `serial` | primary key |
| `email` | `text` | `.notNull().unique()` — stored lowercased |
| `passwordHash` | `text` | `.notNull()` — bcrypt hash, never the plaintext |
| `createdAt` | `timestamp` | `.notNull().defaultNow()` |

**`sessions`** — owned by the schema file so migrations manage it, with the exact column shape
`connect-pg-simple` expects:

| Column | Type | Notes |
|---|---|---|
| `sid` | `text` | primary key |
| `sess` | `json` | `.notNull()` — session payload |
| `expire` | `timestamp` (precision 6) | `.notNull()`, indexed |

No pgEnums are needed. No changes to `projects` or `tasks` — projects are not yet owned by a user,
and adding an owner column is deliberately left to a later spec.

Migrations are generated with `npm run db:generate`, the generated SQL under `src/db/migrations/`
is read and reviewed, and only then applied with `npm run db:migrate`. Migration files are never
hand-written or hand-edited (`app/CLAUDE.md`).

The existing `add-task-field` skill (`.claude/skills/add-task-field/`) covers adding a *column to
an existing table* and does not apply here — these are new tables. Follow its schema → generate →
review → migrate ordering as the general pattern, but not its API/view/seed steps.

## Views

- **Create:** `src/views/login.ejs` — login form posting to `/login`, rendering an `error` message
  when present and re-filling the `email` field. Uses `partials/header` and `partials/footer` like
  every other view.
- **Modify:** `src/views/partials/header.ejs` — add an auth block to `.app-nav`: the signed-in
  user's email plus a `POST /logout` form-button when `currentUser` is set, a `/login` link
  otherwise. The partial must tolerate `currentUser` being undefined, following the existing
  `typeof title !== "undefined"` guard style already in that file.
- **Styles:** additions to `src/public/styles.css` — a `.login-form` block reusing the visual
  language of `.new-project-form`, a `.form-error` message style using `var(--coral)`, and
  `.nav-user` / `.logout-btn` for the header. Use the existing CSS variables; never hardcode hex
  values.

## Constraints

- Passwords are hashed with bcrypt at cost factor 10 or higher. A plaintext or reversibly-encoded
  password must never reach the database, a log line, or a rendered view.
- The session secret comes from `process.env.SESSION_SECRET`. The app must fail fast at startup
  with a clear error if it is missing — never fall back to a hardcoded default.
- Session cookies are `httpOnly: true`, `sameSite: "lax"`, and `secure` only when
  `process.env.NODE_ENV === "production"` (so local HTTP development still works).
- Session lifetime is 24 hours.
- The login failure message is identical for "no such user" and "wrong password", and the code path
  takes comparable time in both cases — do not skip the bcrypt comparison when the user lookup
  misses, or the timing difference discloses which emails are registered.
- Session middleware must be registered in `src/app.ts` *before* `app.use(projectsRouter)` and
  before the page routes, so every downstream handler sees `req.session`.
- The error middleware at the bottom of `src/app.ts` stays the single error handler; its
  `req.path.startsWith("/api")` branch is not modified.
- No new environment variable may be committed with a real value — `.env.example` gets a
  placeholder only.

## Edge cases and error handling

| Case | Expected behaviour | Error class → status |
|---|---|---|
| `POST /login` with missing email or password | Re-render login form with validation message | `ValidationError` → 400 |
| `POST /login` with an email that has no user | Re-render with generic "Invalid email or password"; still run a bcrypt compare against a dummy hash | `AuthError` → 401 |
| `POST /login` with a correct email, wrong password | Identical response to the unknown-email case | `AuthError` → 401 |
| `POST /login` with email differing only in case (`AMIT@x.com`) | Succeeds — lookup is on the lowercased email | — |
| `POST /login` while already logged in | Session is regenerated for the newly authenticated user, then redirect to `/` | — |
| `GET /login` while already logged in | Redirect to `/` without rendering the form | — |
| `POST /logout` with no active session | Redirect to `/login`; not an error | — |
| Unauthenticated `POST` to a guarded HTML route | Redirect to `/login` (not a 401 page — this is a browser form flow) | — |
| Session cookie present but the session row is gone or expired | Treated as unauthenticated; guarded routes redirect to `/login` | — |
| Duplicate email at seed time | Seed fails loudly on the unique constraint rather than creating a second account | `ValidationError` → 400 (API path) / seed throws |
| `SESSION_SECRET` missing at startup | Process exits with a clear message before the server binds a port | throws at boot |

A new `AuthError` subclass is added to `src/lib/errors.ts` alongside `NotFoundError` and
`ValidationError`, carrying status 401 and following the identical constructor shape.

## Files to change

| File | Reason |
|---|---|
| `src/db/schema.ts` | Add the `users` and `sessions` tables |
| `src/db/seed.ts` | Insert seed users with bcrypt-hashed passwords; print the demo credentials |
| `src/app.ts` | Register session middleware before the routers; mount `authRouter`; apply `requireAuth` to the four mutating HTML routes; expose `currentUser` to views |
| `src/lib/errors.ts` | Add the `AuthError` subclass (401) |
| `src/views/partials/header.ejs` | Show signed-in email + logout button, or a login link |
| `src/public/styles.css` | `.login-form`, `.form-error`, `.nav-user`, `.logout-btn` |
| `tests/projects.test.ts` | Extend the `TRUNCATE` in `beforeAll` to include `users` and `sessions` so the suite still resets cleanly |
| `package.json` | New dependencies (below) |
| `.env.example` | Add `SESSION_SECRET` with a placeholder value |
| `app/CLAUDE.md` | Document the auth layer, the seeded demo credentials, and the new env var |

## Files to create

| File | Purpose |
|---|---|
| `src/routes/auth.routes.ts` | `GET /login`, `POST /login`, `POST /logout` handlers |
| `src/lib/password.ts` | `hashPassword` / `verifyPassword` wrappers over bcrypt, plus the dummy-hash constant used for the timing-safe miss path |
| `src/lib/credentials.ts` | `parseCredentials(body)` returning `{ email, password }` or throwing `ValidationError` — follows the `parsePriority` pattern in `task-priority.ts` |
| `src/lib/session.ts` | Session middleware configuration (store, cookie flags, secret validation) |
| `src/middleware/require-auth.ts` | `requireAuth` guard redirecting unauthenticated HTML requests to `/login` |
| `src/types/session.d.ts` | Module augmentation adding `userId` to `express-session`'s `SessionData` |
| `src/views/login.ejs` | The login page |
| `tests/auth.test.ts` | Supertest coverage for the login/logout flow and the route guards |

## New dependencies

| Package | Type | Why |
|---|---|---|
| `express-session` | dependency | Server-side session management |
| `connect-pg-simple` | dependency | Postgres-backed session store, pointed at the Drizzle-owned `sessions` table via its `tableName` option so the schema file stays the source of truth |
| `bcryptjs` | dependency | Password hashing. Chosen over `bcrypt`/`argon2` because it is pure JavaScript and needs no native build step — the series is demoed on Windows |
| `@types/express-session` | devDependency | Types |
| `@types/connect-pg-simple` | devDependency | Types |
| `@types/bcryptjs` | devDependency | Types |

## Rules for implementation

- TypeScript strict is on (`tsconfig.json`) — no `any`, no non-null assertions to silence the
  compiler. Extend `express-session`'s `SessionData` by declaration merging rather than casting.
- Drizzle only — no raw SQL in route handlers, no second ORM. The one permitted exception is the
  existing `sql` template usage for ordering and the `TRUNCATE` in tests.
- `src/db/schema.ts` is the source of truth; generate migrations with `npm run db:generate`, read
  the SQL, then `npm run db:migrate`. Never hand-edit a generated migration.
- Validation helpers live in `src/lib/` and are importable by both route surfaces — follow the
  `parsePriority` shape in `task-priority.ts` (throw `ValidationError` on invalid input present,
  return `undefined` when absent).
- Route handlers `throw` an `AppError` subclass and forward with `next(err)`; never handle errors
  inline. The single middleware at the bottom of `src/app.ts` renders JSON for `/api/*` and the
  `error.ejs` view otherwise. The login form is the one intentional exception: it re-renders
  `login.ejs` with an inline message rather than the generic error page, because a browser login
  failure is expected user flow, not a system error.
- Keep the HTML and JSON surfaces in sync for any resource whose behaviour changes — with the
  documented exception in scope boundary 2, which must not be widened silently.
- All EJS templates use the existing `partials/header` and `partials/footer`.
- No secrets in source — `SESSION_SECRET` goes through `.env`, with only a placeholder in
  `.env.example`.
- Never log a password, a password hash, or a full session payload.

## Definition of done

Verifiable by running `npm run lint`, `npm run test`, and the app at `http://localhost:3000`.

**Schema and setup**
- [ ] `npm run db:generate` produces a migration adding `users` and `sessions`; the SQL has been read before applying
- [ ] `npm run db:migrate` applies cleanly against a fresh database
- [ ] `npm run db:seed` creates the demo users and prints their credentials
- [ ] Starting the app without `SESSION_SECRET` exits with a clear message and never binds a port

**Login (FR 3–6, 12)**
- [ ] `GET /login` returns 200 and renders the form
- [ ] `POST /login` with seeded credentials returns 302 to `/` and sets a session cookie
- [ ] `POST /login` with a wrong password returns 401 and the message "Invalid email or password"
- [ ] `POST /login` with an unknown email returns 401 with a byte-identical body to the wrong-password case
- [ ] `POST /login` with a missing password returns 400 and does not hit the users table
- [ ] `POST /login` with a differently-cased email succeeds
- [ ] `GET /login` while authenticated returns 302 to `/`

**Session and logout (FR 7, 8, 13)**
- [ ] A second request with the session cookie is recognised as authenticated
- [ ] `POST /logout` returns 302 to `/login` and the session cookie no longer authenticates
- [ ] `POST /logout` with no session returns 302 to `/login` without erroring
- [ ] A session row exists in the `sessions` table after login and is gone after logout
- [ ] Restarting `npm run dev` leaves an existing login still valid

**Guards and views (FR 9, 10, 11)**
- [ ] Unauthenticated `POST /projects` returns 302 to `/login` and creates nothing
- [ ] All four mutating HTML routes are guarded; all five read routes still return 200 anonymously
- [ ] Authenticated project and task creation still works end to end in the browser
- [ ] The header shows the signed-in email and a Logout button when authenticated, a Login link otherwise
- [ ] The password field is never echoed back into the rendered HTML

**Regression and quality**
- [ ] All 14 pre-existing tests in `tests/projects.test.ts` still pass unchanged in behaviour
- [ ] `tests/auth.test.ts` covers every bullet in the Login and Session sections above
- [ ] `npm run lint` passes clean
- [ ] `npm run test` passes clean
