# Spec: User Registration Page

## Problem statement

`01-login-logout.md` introduces identity into TaskFlow, but deliberately excludes signup: the only
way an account can exist is `npm run db:seed`, which inserts two hardcoded demo users. That is
enough to demonstrate a login form and nothing else — a second person cannot use the app without a
developer editing `src/db/seed.ts` and re-running the seed against the database. This feature closes
that gap with a self-service registration page: a public `GET /register` form, a `POST /register`
handler that validates the submission, rejects duplicate emails, hashes the password with the same
`src/lib/password.ts` helpers login uses, creates the row in `users`, logs the new account straight
in, and lands them on the dashboard. It is the smallest addition that makes the auth layer complete
enough to hand to someone else.

## Depends on

**`01-login-logout.md` must be implemented and merged first.** This spec is additive to that one and
reuses its artefacts rather than re-creating them. Specifically it assumes these already exist:

| Artefact from spec 01 | How this spec uses it |
|---|---|
| `users` table in `src/db/schema.ts` (`id`, `email` unique, `passwordHash`, `createdAt`) | Inserts a row; adds no columns |
| `sessions` table + `express-session` middleware wired in `src/app.ts` | Establishes the session for the newly created user |
| `src/lib/password.ts` (`hashPassword`) | Hashes the submitted password — no second hashing implementation |
| `src/lib/errors.ts` → `AuthError` (401) | Not thrown here, but the file's shape is extended for `ConflictError` |
| `src/views/login.ejs`, `.login-form` / `.form-error` styles | `register.ejs` mirrors its markup and reuses its CSS |
| `src/routes/auth.routes.ts` | The two new routes are added to this existing router, not a new one |
| `requireAuth` middleware (`src/middleware/require-auth.ts`) | Read-only reference — registration is public and is **not** guarded |

At the time of writing, spec 01 exists as a document on `feature/login-logout` but is **not
implemented on `main`** — no `users` table, no session middleware, no `auth.routes.ts`. If
implementation of this spec begins before 01 has landed, stop and land 01 first; every "Files to
change" entry below assumes 01's version of that file.

## Functional requirements

1. `GET /register` renders a registration page with email, password, and confirm-password fields.
2. `GET /register` while already authenticated redirects to `/` without rendering the form.
3. `POST /register` with a valid, unused email and a matching password pair creates exactly one row
   in `users`.
4. The stored `passwordHash` is a bcrypt hash produced by `hashPassword`; the plaintext password is
   never persisted, logged, or rendered.
5. The email is stored lowercased and trimmed, so `Amit@Example.com` and `amit@example.com` are the
   same account.
6. A successful registration establishes a session for the new user and redirects to `/`, with no
   second trip through the login form.
7. `POST /register` with an email that already exists re-renders the form with a message naming the
   conflict, and creates no row.
8. `POST /register` where password and confirm-password differ re-renders the form with a mismatch
   message, and does not query or write the `users` table.
9. `POST /register` with a password shorter than 8 characters re-renders the form with a length
   message, and creates no row.
10. `POST /register` with a missing or structurally invalid email re-renders the form with a
    validation message, and creates no row.
11. On any failed registration, the submitted email is re-filled into the form and neither password
    field is echoed back into the rendered HTML.
12. The login page links to `/register`, and the registration page links back to `/login`.
13. The header shows a Register link alongside Login when no session exists, and neither when a
    session does.
14. `POST /api/users` creates an account over the JSON surface and returns the new user without its
    password hash.

## Routes

**HTML (form-post, rendered EJS — added to `src/routes/auth.routes.ts` from spec 01)**

- `GET /register` — render the registration form — public (redirects to `/` if already authenticated)
- `POST /register` — validate, create the user, establish a session, redirect to `/` — public

**JSON API (added to a new `src/routes/users.routes.ts`, mounted under `/api/*` in `src/app.ts`)**

- `POST /api/users` — create an account from a JSON body — public

Both surfaces are implemented because `.claude/rules/architecture.md` is referenced by the
`/create-spec` command but does not exist in this repo; the authoritative rule is `app/CLAUDE.md`'s
"decide whether it needs both surfaces or just one, and keep validation shared between them via a
helper in `src/lib/`". Account creation is a real API operation with an obvious contract, so it gets
both, with **one deliberate behavioural difference**: `POST /api/users` creates the account but does
**not** establish a session. A session is a browser-cookie concern; an API caller that wants one uses
the HTML flow. This difference is stated in the contract below so it is not mistaken for a bug.

Registration is public on both surfaces by definition — it is the one write operation that cannot
require an existing session. It therefore does not widen spec 01's scope boundary 2 (the
unauthenticated `/api/*` surface): `POST /api/users` would be public even after
`03-api-authentication` gates the rest.

**Changed behaviour on existing routes** — none. `GET /login` gains a link to `/register` in its
template only.

## API contracts

**`POST /api/users`**

Request — `application/json`:

| Field | Type | Required | Notes |
|---|---|---|---|
| `email` | `string` | yes | Trimmed and lowercased before validation and insert |
| `password` | `string` | yes | Minimum 8 characters, compared as given (never trimmed) |

`confirmPassword` is **not** part of the JSON contract — confirmation is a form-UX affordance, not a
property of the resource. Sending it is ignored, not an error.

Success — `201 Created`:

```json
{ "id": 3, "email": "new@example.com", "createdAt": "2026-08-10T12:00:00.000Z" }
```

`passwordHash` must never appear in the response body. Select the three returned columns explicitly
in the Drizzle `.returning({ ... })` call rather than returning the whole row and deleting a key.

Errors:

| Status | Body | When |
|---|---|---|
| `400` | `{ "error": "email is required" }` | `email` missing, empty, or not a string |
| `400` | `{ "error": "email must be a valid email address" }` | Email fails the format check |
| `400` | `{ "error": "password is required" }` | `password` missing, empty, or not a string |
| `400` | `{ "error": "password must be at least 8 characters" }` | Password too short |
| `409` | `{ "error": "An account with that email already exists" }` | Email already in `users` |

**HTML form contracts**

`GET /register` — `200`, renders `register.ejs`. If authenticated: `302` to `/`.

`POST /register` — `application/x-www-form-urlencoded` with `email`, `password`, `confirmPassword`.

- Success: `302` to `/`, `Set-Cookie` with the session id for the new user
- Validation failure: `400`, renders `register.ejs` with `{ error: <message>, email: <submitted> }`
- Duplicate email: `409`, renders `register.ejs` with the same shape and the conflict message

Like the login form in spec 01, the registration form re-renders itself with an inline message
instead of routing to the generic `error.ejs` page — a rejected signup is expected user flow, not a
system error. This is the same documented exception, applied to the same kind of route, and it does
not extend to `POST /api/users`, which goes through `next(err)` and the JSON branch of the error
middleware as normal.

## Database changes

**No database changes.** The `users` table created by spec 01 already has every column this feature
writes (`email`, `passwordHash`, `createdAt`) and its `.unique()` constraint on `email` is what makes
requirement 7 enforceable at the database level rather than only in application code.

Because no column is added, the `add-task-field` skill (`.claude/skills/add-task-field/`) does not
apply — that skill's whole subject is adding a column to `tasks` or `projects`. No `npm run
db:generate` / `npm run db:migrate` cycle is needed for this spec. If implementation discovers that
`users` is missing or shaped differently, that is a signal spec 01 has not landed — stop and finish
01 rather than patching the schema here.

## Views

- **Create:** `src/views/register.ejs` — email, password, and confirm-password fields posting to
  `/register`; renders `error` when present; re-fills `email`; links to `/login`. Uses
  `partials/header` and `partials/footer` and the `.login-form` / `.form-error` classes from spec 01
  so the two auth pages are visually identical.
- **Modify:** `src/views/login.ejs` — add a "Need an account? Register" link to `/register`.
- **Modify:** `src/views/partials/header.ejs` — add a `/register` link to the anonymous branch of the
  auth block spec 01 adds to `.app-nav`, keeping that file's `typeof … !== "undefined"` guard style.
- **Styles:** `src/public/styles.css` — a `.form-hint` style for the "already have an account?" line
  and `input[type="password"]` added to the existing `input[type="text"], select` selector block so
  password inputs pick up the same surface, border, radius, and colour. Use the existing CSS
  variables (`--surface`, `--border`, `--white`, `--muted`, `--coral`); never hardcode a hex value.
  No new colour is introduced.

## Constraints

- Reuse `hashPassword` from `src/lib/password.ts`. Do not import bcrypt directly in a route handler
  and do not introduce a second cost factor — one hashing policy for the app.
- Email format validation is a single small regex or equivalent check in `src/lib/credentials.ts`
  (requiring a local part, `@`, a domain with a dot). Do not add an email-validation dependency, and
  do not attempt RFC-complete validation — TaskFlow is a demo app.
- The minimum password length (8) is a named exported constant, not a literal repeated across the
  validator, the view, and the tests.
- The duplicate-email check must not rely solely on a pre-insert `SELECT`. Two concurrent signups can
  both pass that check; the insert must be wrapped so a unique-constraint violation from Postgres is
  translated into the same `ConflictError` → 409 as the pre-check. Detect it by Postgres error code
  `23505`, not by string-matching the message.
- Unlike login, the failure messages here are intentionally specific ("that email already exists").
  Spec 01's generic message exists to avoid disclosing which emails are registered; a registration
  form cannot hide that and stay usable, since it must tell the user why their signup failed. This is
  an accepted, bounded disclosure on a localhost demo app — do not "fix" it by making the message
  generic, and do not copy this reasoning back into the login handler.
- Session establishment on success must regenerate the session id before storing `userId`, so a
  pre-existing anonymous session cannot be fixated onto the new account.
- Registration is not rate-limited and no email verification is sent. Both are out of scope for this
  spec and must not be half-built here.
- `POST /register` and `POST /api/users` must never be placed behind `requireAuth`.
- No new environment variables. No secrets in source.

## Edge cases and error handling

| Case | Expected behaviour | Error class → status |
|---|---|---|
| Missing `email` | Re-render form / JSON error; no DB write | `ValidationError` → 400 |
| Email with no `@` or no domain dot | Re-render form / JSON error; no DB write | `ValidationError` → 400 |
| Email differing only in case from an existing user | Rejected as a duplicate — comparison is on the lowercased value | `ConflictError` → 409 |
| Email with surrounding whitespace | Trimmed, then validated and stored | — |
| Missing `password` | Re-render form / JSON error; no DB write | `ValidationError` → 400 |
| Password shorter than 8 characters | Re-render form / JSON error; no DB write | `ValidationError` → 400 |
| `confirmPassword` missing or different (HTML only) | Re-render form with mismatch message; `users` is never queried | `ValidationError` → 400 |
| Password of only whitespace, 8+ characters | Accepted — passwords are never trimmed, so it is a valid 8-character secret | — |
| Duplicate email caught by the pre-insert lookup | Re-render / JSON 409; no row created | `ConflictError` → 409 |
| Duplicate email caught by the unique constraint (race) | Identical response to the pre-insert case | `ConflictError` → 409 |
| `POST /register` while already logged in | Session is regenerated for the new account, then redirect to `/` — not an error | — |
| `GET /register` while already logged in | Redirect to `/` without rendering the form | — |
| Double-submitted form (same body twice) | First creates the account; second is a duplicate → 409, still exactly one row | `ConflictError` → 409 |
| Any failed attempt | `password` and `confirmPassword` absent from the rendered HTML | — |
| `users` table absent (spec 01 not landed) | Stop — this is a missing dependency, not a runtime case to handle | — |

A new `ConflictError` subclass is added to `src/lib/errors.ts` alongside `NotFoundError`,
`ValidationError`, and spec 01's `AuthError`, carrying status 409 and the identical constructor shape
(`constructor(message = "Conflict") { super(message, 409); }`).

## Files to change

| File | Reason |
|---|---|
| `src/lib/errors.ts` | Add the `ConflictError` subclass (409) |
| `src/lib/credentials.ts` | Add `parseRegistration(body)` beside spec 01's `parseCredentials`, plus the exported `MIN_PASSWORD_LENGTH` and the email format check |
| `src/routes/auth.routes.ts` | Add `GET /register` and `POST /register` |
| `src/app.ts` | Mount the new `usersRouter` alongside `projectsRouter`, after the session middleware |
| `src/views/login.ejs` | Link to `/register` |
| `src/views/partials/header.ejs` | Add the `/register` link to the anonymous nav branch |
| `src/public/styles.css` | `.form-hint`; include `input[type="password"]` in the existing input block |
| `tests/projects.test.ts` | No behavioural change — confirm the `TRUNCATE` spec 01 extends to `users`/`sessions` still resets state for the new tests |
| `app/CLAUDE.md` | Document the registration routes and that account creation is public on both surfaces |
| `.claude/specs/01-login-logout.md` | Update scope boundary 1's forward reference so it points at `02-user-registration-page` |

## Files to create

| File | Purpose |
|---|---|
| `src/lib/user-service.ts` | `createUser({ email, password })` — hashes, inserts, translates a `23505` unique violation into `ConflictError`; the single account-creation path shared by both route surfaces |
| `src/routes/users.routes.ts` | `POST /api/users` handler |
| `src/views/register.ejs` | The registration page |
| `tests/register.test.ts` | Supertest coverage for both surfaces: success, duplicate, mismatch, short password, bad email, no-hash-in-response |

## New dependencies

**No new dependencies.** Everything this feature needs — `bcryptjs`, `express-session`,
`connect-pg-simple` and their `@types` — is already added by spec 01. No email-validation or
rate-limiting package is introduced.

## Rules for implementation

- TypeScript strict — no `any`, no non-null assertions to silence the compiler. Narrow `unknown`
  request-body values with real type checks, as `parsePriority` does.
- Drizzle only — no raw SQL in route handlers, no other ORM. Reading `error.code === "23505"` off the
  caught `pg` error is permitted, and belongs in `src/lib/user-service.ts`, not in a handler.
- `src/db/schema.ts` is the source of truth; generate migrations, never hand-edit them. This spec
  needs no migration.
- Validation helpers live in `src/lib/` and are shared by both route surfaces — follow the
  `parsePriority` pattern in `task-priority.ts` (throw `ValidationError` on invalid input, return
  `undefined` for absent-and-optional). `parseRegistration` is imported by both
  `auth.routes.ts` and `users.routes.ts`; neither surface gets its own copy of a rule.
- Route handlers `throw` an `AppError` subclass and forward with `next(err)` — never handle errors
  inline; the single middleware at the bottom of `src/app.ts` renders JSON for `/api/*` and the
  `error.ejs` view otherwise. The one exception is `POST /register`, which catches its own
  `ValidationError` / `ConflictError` to re-render `register.ejs` inline — exactly as spec 01's
  `POST /login` does, and for the same reason. Every other error still goes to `next(err)`.
- Keep the HTML and JSON surfaces in sync: both call `createUser` from `src/lib/user-service.ts`, so
  validation, hashing, and duplicate handling cannot drift. The only permitted difference is session
  establishment, documented above.
- All EJS templates use the existing `partials/header` and `partials/footer`.
- No secrets in source — this spec adds no configuration.
- Never log the password, the hash, or the full session payload.

## Definition of done

Verifiable by running `npm run lint`, `npm run test`, and the app at `http://localhost:3000`.

**Registration page (FR 1, 2, 11, 12, 13)**
- [ ] `GET /register` returns 200 and renders email, password, and confirm-password fields
- [ ] `GET /register` while authenticated returns 302 to `/`
- [ ] After any failed submission, neither password value appears anywhere in the response body
- [ ] After any failed submission, the submitted email is re-filled in the form
- [ ] `/login` links to `/register` and `/register` links back to `/login`
- [ ] The header shows Login and Register when anonymous, and neither when authenticated

**Account creation (FR 3, 4, 5, 6)**
- [ ] `POST /register` with a fresh email returns 302 to `/` and sets a session cookie
- [ ] Exactly one `users` row exists afterwards, and its `passwordHash` is neither the plaintext nor
      equal for two users registered with the same password
- [ ] The new user can immediately load `/` and see their email in the header without logging in
- [ ] The account created via `/register` can then log in through `POST /login` with the same
      credentials
- [ ] Registering `Amit@Example.com` stores `amit@example.com`, and logging in with either casing works

**Validation and conflicts (FR 7, 8, 9, 10)**
- [ ] `POST /register` with an existing email returns 409, renders the conflict message, and leaves
      the `users` row count unchanged
- [ ] Registering the same email in a differing case is also rejected with 409
- [ ] `POST /register` with mismatched passwords returns 400 and creates no row
- [ ] `POST /register` with a 7-character password returns 400 and creates no row
- [ ] `POST /register` with `email=notanemail` returns 400 and creates no row
- [ ] Submitting the identical valid body twice yields one 302 and one 409, with exactly one row

**JSON surface (FR 14)**
- [ ] `POST /api/users` with a valid body returns 201 and a body of exactly `id`, `email`, `createdAt`
- [ ] The 201 response body contains no `passwordHash` key
- [ ] `POST /api/users` with a duplicate email returns 409 and `{ "error": … }`
- [ ] `POST /api/users` with a short password returns 400 and `{ "error": … }`
- [ ] `POST /api/users` sets no session cookie
- [ ] A user created via `POST /api/users` can log in at `POST /login`

**Regression and quality**
- [ ] Every test in `tests/projects.test.ts` still passes unchanged
- [ ] Every test in `tests/auth.test.ts` (spec 01) still passes unchanged
- [ ] `tests/register.test.ts` covers every bullet in the three sections above
- [ ] `npm run lint` passes clean
- [ ] `npm run test` passes clean
