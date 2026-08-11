# Implementation Plan: 01 — Login and Logout

## Context

TaskFlow (`app/`) has no concept of a user. `src/db/schema.ts` holds only `projects` and `tasks`,
`src/app.ts` has no session middleware, and any visitor to `http://localhost:3000` can create or
delete any project or task anonymously. `.claude/specs/01-login-logout.md` specifies the first
identity layer: a `users` table with bcrypt-hashed passwords, a Postgres-backed session, a login page,
a logout action, and a `requireAuth` guard on the four HTML routes that mutate data. The JSON API
under `/api/*` stays deliberately unauthenticated (spec 01, scope boundary 2) so the existing 14 tests
in `tests/projects.test.ts` keep passing.

This plan is the execution order for that spec. It exists because the auth layer touches the app's
bootstrap sequence — middleware order, module-load-time config validation, and shared test-database
state — and getting those in the wrong order produces failures that look unrelated to auth. Outcome:
spec 01's Definition of done passes, and `02-user-registration-page.md` (already written, and blocked
on this) becomes implementable.

## Decisions and spec corrections

Four things found while reading the codebase and the registry that the spec gets wrong or leaves open.
These are settled here so implementation doesn't stall on them.

1. **Do not install `@types/bcryptjs`.** The spec lists it as a devDependency, but `bcryptjs@3.0.3`
   ships its own types (`umd/index.d.ts`), and `@types/bcryptjs@3.0.0` is a published *stub* marked
   deprecated: *"bcryptjs provides its own type definitions, so you do not need this installed."*
   Install `bcryptjs` alone.
2. **`@types/connect-pg-simple` lags the runtime package.** `connect-pg-simple` is at `10.0.0` and
   ships no `types` field; the only stub available is `@types/connect-pg-simple@7.0.3`. Install the
   stub and compile; if it does not typecheck against v10, pin `connect-pg-simple` to `^7` rather than
   casting to `any` (tsconfig has `strict: true`).
3. **Test-file parallelism becomes a real hazard.** There is one test file today, so shared database
   state is safe by accident. Adding `tests/auth.test.ts` breaks that: vitest runs test *files* in
   parallel, and the spec requires `tests/projects.test.ts` to `TRUNCATE … users, sessions`, which
   would delete `auth.test.ts`'s logged-in user mid-run. Add `fileParallelism: false` to
   `vitest.config.ts`. The alternative — per-file unique fixtures and no cross-table truncation —
   spreads the constraint across every future test file instead of stating it once.
4. **The "byte-identical body" check in the spec's Definition of done is not literally achievable.**
   Both failure paths render `login.ejs` with the same message, but the view also re-fills the
   submitted email, so an unknown-email response and a wrong-password response differ in that field by
   construction. Assert byte-identical bodies for *the same submitted email* under two different
   passwords (one belonging to a real user, one not), plus an identical rendered error message across
   the unknown-email and wrong-password cases. The security property — not disclosing which emails are
   registered — is preserved.

## Sequence

### Phase 0 — Branch, env, dependencies

- Create the implementation branch off `main` (see the question resolved with the user; the current
  checkout is `feature/user-registration-page`, which belongs to spec 02).
- `npm install bcryptjs express-session connect-pg-simple` and
  `npm install -D @types/express-session @types/connect-pg-simple` — per decision 1, no
  `@types/bcryptjs`.
- Add `SESSION_SECRET=change-me-in-your-local-env` to `app/.env.example`, and add a real value to your
  local `app/.env`. **This is required before any test can run** — see Gotcha A.

### Phase 1 — Schema and migration

`src/db/schema.ts` is the source of truth; both tables are new, so the `add-task-field` skill does not
apply.

- `users`: `id` serial PK, `email` text `.notNull().unique()`, `passwordHash` text `.notNull()`,
  `createdAt` timestamp `.notNull().defaultNow()`. Follow the existing `projects` declaration style.
- `sessions`: `sid` text PK, `sess` json `.notNull()`, `expire` timestamp `{ precision: 6 }`
  `.notNull()`, plus an index on `expire`. This is the exact column shape `connect-pg-simple` expects
  — Drizzle owns the table so migrations manage it, and the store is pointed at it by name rather than
  creating its own.
- No pgEnums. No change to `projects` or `tasks` — project ownership is a later spec.
- `npm run db:generate` → **read the generated SQL** under `src/db/migrations/` (it will be `0002_*`;
  `0000` and `0001` already exist) → `npm run db:migrate`. Never hand-edit the generated file.

### Phase 2 — Library primitives

Small, testable units first, so the route handlers in Phase 4 are assembly rather than logic.

- `src/lib/errors.ts` — add `AuthError extends AppError` with status 401, same constructor shape as
  `NotFoundError` / `ValidationError` (`constructor(message = "…") { super(message, 401); }`).
- `src/lib/password.ts` — `hashPassword(plain)` and `verifyPassword(plain, hash)` over `bcryptjs` at
  cost factor 10+, plus the exported `DUMMY_HASH` constant (a real bcrypt hash of an unguessable
  string) used on the user-lookup-miss path. One hashing policy, one cost factor, defined here only.
- `src/lib/credentials.ts` — `parseCredentials(body)` returning `{ email, password }` or throwing
  `ValidationError`. Follow the `parsePriority` shape in `src/lib/task-priority.ts`: narrow `unknown`
  with real type checks, throw on invalid. Email is trimmed and lowercased; **password is never
  trimmed** — leading/trailing whitespace is significant.
- `src/lib/session.ts` — the `express-session` configuration: `connect-pg-simple` store constructed
  with the **existing `pool` exported from `src/db/client.ts`** (do not open a second pool),
  `tableName: "sessions"` (the store's default is the singular `session`), `createTableIfMissing:
  false`, `resave: false`, `saveUninitialized: false`, cookie `{ httpOnly: true, sameSite: "lax",
  secure: process.env.NODE_ENV === "production", maxAge: 24h }`, and a secret read from
  `process.env.SESSION_SECRET` that throws a clear error when missing.
- `src/types/session.d.ts` — declaration merging on `express-session`'s `SessionData` to add
  `userId?: number`. No casts, no non-null assertions (tsconfig `strict`, `rootDir: "src"`).

### Phase 3 — Middleware

- `src/middleware/require-auth.ts` — `requireAuth`: if `req.session.userId` is absent,
  `res.redirect("/login")`; otherwise `next()`. A browser form flow gets a redirect, not a 401 page.
- A `loadCurrentUser` middleware (same folder) — when `req.session.userId` is set, look the user up
  with Drizzle and assign `res.locals.currentUser = { id, email }`. `res.locals` merges into every
  `res.render`, and EJS `include` inherits the parent's data, so `partials/header.ejs` sees
  `currentUser` without any view needing to pass it explicitly. Never put the hash on `res.locals`.

### Phase 4 — Routes and app wiring

- `src/routes/auth.routes.ts` — a `Router` following `projects.routes.ts`'s structure:
  - `GET /login` — redirect to `/` if `req.session.userId` is set (FR 12), else render `login.ejs`.
  - `POST /login` — `parseCredentials` → look up by lowercased email → `verifyPassword` against the
    real hash, **or against `DUMMY_HASH` when the lookup misses** so both paths cost the same time →
    on success `req.session.regenerate(…)`, set `userId`, `req.session.save(…)`, redirect to `/`.
    Wrap the callback-based `regenerate`/`save` in a small promise helper rather than nesting.
  - `POST /login` failures are the **one documented exception** to the throw-and-`next(err)` rule:
    catch `ValidationError`/`AuthError` and re-render `login.ejs` inline with
    `res.status(err.statusCode).render("login", { error: err.message, email })`. Take the status and
    message off the error object so they are defined in one place. Any other error still goes to
    `next(err)`.
  - `POST /logout` — destroy the session, clear the cookie, redirect to `/login`; a request with no
    session redirects too, without erroring (idempotent).
- `src/app.ts`:
  - Insert `app.use(sessionMiddleware)` then `app.use(loadCurrentUser)` **after** `express.json()` and
    **before** `app.use(projectsRouter)` and every page route, so all downstream handlers see
    `req.session`. `express.static` stays first, so asset requests never touch the session store.
  - Mount `authRouter`.
  - Add `requireAuth` to exactly four routes: `POST /projects`, `POST /projects/:id/delete`,
    `POST /projects/:id/tasks`, `POST /projects/:projectId/tasks/:id/delete`. Leave `GET /`,
    `GET /projects/:id`, `GET /about`, `GET /terms`, `GET /privacy` public (FR 11).
  - Do not touch the error middleware at the bottom or its `req.path.startsWith("/api")` branch.

### Phase 5 — Views and styles

- Create `src/views/login.ejs` — posts to `/login`, renders `error` when present, re-fills `email`,
  never echoes the password. Uses `partials/header` and `partials/footer` like every other view.
- Modify `src/views/partials/header.ejs` — an auth block in `.app-nav`: signed-in email plus a
  `POST /logout` form-button when `currentUser` is set, a `/login` link otherwise. Guard with the
  file's existing `typeof … !== "undefined"` style so a render without locals cannot crash.
- Modify `src/public/styles.css` — `.login-form` (mirroring `.new-project-form`), `.form-error` using
  `var(--coral)`, `.nav-user`, `.logout-btn`. Add `input[type="password"]` to the existing
  `input[type="text"], select` block so password fields inherit the surface/border/radius. Use the
  existing variables only — no new hex values.

### Phase 6 — Seed

- `src/db/seed.ts` — insert at least two users with `hashPassword`-generated hashes before the existing
  project/task inserts, and `console.log` the demo credentials so the login page is usable straight
  after setup. Plaintext passwords appear in the seed source and its output by design; the hash is what
  reaches the database.

### Phase 7 — Tests

- `vitest.config.ts` — add `fileParallelism: false` (decision 3).
- `tests/projects.test.ts` — extend the `beforeAll` truncation to
  `TRUNCATE TABLE ${tasks}, ${projects}, ${sessions}, ${users} RESTART IDENTITY CASCADE`. No test
  behaviour changes; all 14 must still pass, which is the check that scope boundary 2 held.
- Create `tests/auth.test.ts` — mirror `projects.test.ts`'s shape (`import "dotenv/config"`, truncate
  in `beforeAll`, `pool.end()` in `afterAll`). Use `request.agent(app)` to carry the session cookie
  across requests. Cover: renders the form; login success 302 + `Set-Cookie`; wrong password 401;
  unknown email 401 with an identical message and the same-email byte-identical comparison from
  decision 4; missing password 400; mixed-case email succeeds; `GET /login` while authenticated 302;
  session recognised on a second request; logout 302 and cookie no longer authenticates; logout with
  no session 302; a `sessions` row exists after login and is gone after logout; unauthenticated
  `POST /projects` 302 to `/login` and creates nothing; all five read routes 200 anonymously.

### Phase 8 — Documentation

- `app/CLAUDE.md` — document the auth layer, the seeded demo credentials, `SESSION_SECRET` as a
  required env var, and the sequential-test-file constraint.
- `.claude/specs/02-user-registration-page.md` — its "Depends on" section states that spec 01 is not
  yet implemented on `main`; update that line once this lands.

## Gotchas

**A. `SESSION_SECRET` fail-fast will break the whole test suite, not just the server.**
`tests/*.test.ts` import `../src/app`, which now constructs the session middleware at module load. If
the secret is validated at import time and is missing, *every* test file fails at import with an error
that says nothing about auth. Two consequences: add `SESSION_SECRET` to your local `app/.env` in Phase
0, and prefer validating inside a `createSessionMiddleware()` function called during app construction
over a bare top-level `throw`, so the failure has a stack that points at the app.

**B. `connect-pg-simple`'s default table name is `session`, not `sessions`.** Pass
`tableName: "sessions"` or the store will silently query a table the migration never created.

**C. `pruneSessionInterval` keeps a timer alive.** The store's default is a periodic `DELETE` every
60s, which can leave an open handle after `pool.end()` and produce hanging or "logged after teardown"
noise in vitest. Disable it when `NODE_ENV === "test"`.

**D. `saveUninitialized: false` is load-bearing.** With it true, every anonymous request writes a
`sessions` row and the "a session row exists after login" check stops proving anything.

**E. Don't skip the bcrypt compare on a lookup miss.** Returning early when no user is found makes the
unknown-email path measurably faster than the wrong-password path and discloses which emails are
registered. That is what `DUMMY_HASH` is for.

**F. `npm run build` does not typecheck the tests.** `tsconfig.json` has `include: ["src"]`, and vitest
transpiles via esbuild without typechecking — a type error in `tests/auth.test.ts` will not fail either
command. Read test types deliberately; the compiler won't catch them.

**G. Session fixation.** Set `userId` only *after* `req.session.regenerate(…)` succeeds, so a
pre-existing anonymous session id cannot be carried into the authenticated session.

## Verification

Run from `app/`, with Postgres up (`docker compose up -d`) and `SESSION_SECRET` set in `.env`:

```bash
npm run db:generate     # review the generated 0002_*.sql before applying
npm run db:migrate
npm run db:seed         # prints the demo credentials
npm run lint            # must pass clean
npm run test            # 14 existing + the new auth tests, all green
npx vitest run tests/auth.test.ts    # iterate on just the new file
npm run dev             # http://localhost:3000
```

Then in the browser, walk the spec's Definition of done:

1. `GET /` anonymously — dashboard renders, header shows a Login link.
2. `POST /projects` anonymously (submit the dashboard form) — lands on `/login`, no project created.
3. Log in with a seeded credential — redirected to `/`, header shows the email and a Logout button.
4. Create a project and a task — both work end to end.
5. Reload, then restart `npm run dev` and reload again — still logged in (the session is in Postgres,
   not memory).
6. Log in with a wrong password — 401, the form re-renders with "Invalid email or password", and
   **view source** to confirm the password is not echoed anywhere.
7. Log in with an unknown email — the same message, and the same status.
8. Visit `/login` while logged in — redirected to `/`.
9. Log out — redirected to `/login`; the back button plus a reload does not restore the session.
10. Unset `SESSION_SECRET` and run `npm run dev` — it exits with a clear message and never binds a
    port. Restore it afterwards.

Database-level confirmation:

```bash
docker compose exec postgres psql -U taskflow -d taskflow \
  -c "select id, email, left(password_hash, 7) from users;" \
  -c "select sid, expire from sessions;"
```

The hash prefix must read `$2a$10$` or `$2b$10$` (never the plaintext), and the `sessions` row must
appear after login and be gone after logout.
