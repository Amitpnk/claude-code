---
description: Create a spec file and feature branch for the next TaskFlow feature
argument-hint: "Feature name e.g. authentication page"
allowed-tools: Read, Write, Glob, Grep, Bash(git:*)
---

You are a senior developer spinning up a new feature for TaskFlow, the
Node/TypeScript/Express/Postgres demo app in `app/`. Always follow the rules in
`app/CLAUDE.md` and every file in `.claude/rules/`.

User input: $ARGUMENTS

## Step 1 — Check working directory is clean
Run `git status --porcelain` and check for uncommitted, unstaged, or untracked
files. If any exist, stop immediately and tell the user to commit or stash
changes before proceeding. DO NOT CONTINUE until the working directory is clean.

## Step 2 — Parse the arguments
From $ARGUMENTS extract:

1. `feature_title` — human readable title in Title Case
   - Example: "Authentication Page" or "Task Due Dates"

2. `feature_slug` — git and file safe slug
   - Lowercase, kebab-case
   - Only a-z, 0-9 and -
   - Maximum 40 characters
   - Example: authentication-page, task-due-dates

3. `branch_name` — format: `feature/<feature_slug>`
   - Example: `feature/authentication-page`

If $ARGUMENTS is empty or you cannot infer a feature from it, ask the user to
clarify before proceeding.

## Step 3 — Determine the spec number
Glob `.claude/specs/*.md`. Take the highest leading number and add 1.
If the directory is empty or missing, start at 1.
Zero-pad to 2 digits: 1 → 01, 11 → 11. This is `spec_number`.

If an existing spec already covers this feature, warn the user and stop rather
than writing a duplicate.

## Step 4 — Check branch name is not taken
Run `git branch --list` to list existing branches.
If `branch_name` is already taken, append a number:
`feature/authentication-page-01`, `feature/authentication-page-02` etc.

## Step 5 — Switch to main and pull latest
Run:
```
git checkout main
git pull origin main
```

## Step 6 — Create and switch to the feature branch
Run:
```
git checkout -b <branch_name>
```

## Step 7 — Research the codebase
Read these before writing the spec — the spec must describe this codebase as it
actually is, not a generic Express app:

- `app/CLAUDE.md` — commands, architecture, conventions
- `.claude/rules/architecture.md` — dual route surface, error handling, validation rules
- `.claude/rules/api-style.md` — paths, status codes and body shapes the API contracts must match
- `.claude/rules/database.md` — schema-to-migration workflow, enum and relation conventions
- `.claude/rules/code-style.md` — strict-TS and naming rules the implementation section must state
- `.claude/rules/testing.md` — shared-DB test constraints the definition of done relies on
- `app/src/db/schema.ts` — current tables, pgEnums, relations
- `app/src/app.ts` — HTML form-post routes, middleware order, error middleware
- `app/src/routes/projects.routes.ts` — the JSON API surface under `/api/*`
- `app/src/lib/` — `errors.ts` and `task-priority.ts` (the validator pattern)
- `app/src/views/` — existing EJS templates and partials
- `app/tests/projects.test.ts` — how tests are written against the real DB
- All files in `.claude/specs/` — avoid duplicating existing specs

Also check whether a Skill in `.claude/skills/` already covers part of this work
(e.g. `add-task-field` for new columns) and reference it in the spec instead of
restating its steps.

## Step 8 — Write the spec
Generate a spec document with this exact structure:

---
# Spec: <feature_title>

## Problem statement
One paragraph: what's missing or broken, and why this feature exists now.

## Depends on
Which existing features or specs must be in place first.
If none: state "No dependencies".

## Functional requirements
Numbered list of what the system must do, behaviour by behaviour.
Each item must be a single, verifiable behaviour — not a bundle.

## Routes
Every new or changed route, on BOTH surfaces where applicable:

**HTML (form-post, rendered EJS — `src/app.ts`)**
- `METHOD /path` — description — access level (public / authenticated)

**JSON API (`src/routes/projects.routes.ts` or a new router under `/api/*`)**
- `METHOD /api/path` — description — access level

If a route belongs on only one surface, say so explicitly and why.
If no new routes: state "No new routes".

## API contracts
For each JSON endpoint: request shape (body/params/query with types), success
response shape and status code, and error response shapes with status codes.
Be concrete about field names and types — this is the contract implementation
must match.

## Database changes
New tables, columns, pgEnums, constraints, or indexes.
Verify against `app/src/db/schema.ts` before writing this.
State that migrations are generated via `npm run db:generate` and reviewed
before `npm run db:migrate` — never hand-written.
If none: state "No database changes".

## Views
- **Create:** new `.ejs` templates with their path
- **Modify:** existing templates and what changes
- **Styles:** additions to `src/public/styles.css`
If none: state "No view changes".

## Constraints
Technical, UX, or security limits the solution must respect.

## Edge cases and error handling
Table or list of: the case → the expected behaviour → the `AppError` subclass
and HTTP status. Cover at minimum bad input, missing resource, duplicate
submission, and unauthenticated access where relevant.

## Files to change
Every file that will be modified, with a one-line reason each.

## Files to create
Every new file that will be created, with a one-line purpose each.

## New dependencies
Any new npm packages, with why each is needed and whether it's a `dependency`
or `devDependency`. If none: state "No new dependencies".

## Rules for implementation
Specific constraints Claude must follow. Always include:
- TypeScript strict — no `any`, no non-null assertions to silence the compiler
- Drizzle only — no raw SQL in route handlers, no other ORM
- `src/db/schema.ts` is the source of truth; generate migrations, never hand-edit them
- Validation helpers live in `src/lib/` and are shared by both route surfaces
  (follow the `parsePriority` pattern in `task-priority.ts`)
- Route handlers `throw` an `AppError` subclass and forward with `next(err)` —
  never handle errors inline; the single middleware in `src/app.ts` renders JSON
  for `/api/*` and the `error.ejs` view otherwise
- Keep the HTML and JSON surfaces in sync — if behaviour changes for a resource,
  update both, not just one
- All EJS templates use the existing `partials/header` and `partials/footer`
- No secrets in source — new config goes through `.env` and `.env.example`

## Definition of done
A specific, testable checklist. Each item must be verifiable by running
`npm run lint`, `npm run test`, or the app itself at `http://localhost:3000`.
Include at least one item per functional requirement, and require that
`npm run lint` and `npm run test` both pass clean.
---

## Step 9 — Save the spec
Save to: `.claude/specs/<spec_number>-<feature_slug>.md`
Create the `.claude/specs/` directory if it does not exist.

## Step 10 — Report to the user
Print a short summary in this exact format:
```
Branch:    <branch_name>
Spec file: .claude/specs/<spec_number>-<feature_slug>.md
Title:     <feature_title>
```

Then tell the user:
"Review the spec at `.claude/specs/<spec_number>-<feature_slug>.md`
then enter Plan Mode with Shift+Tab twice to begin implementation."

Do not print the full spec in chat unless explicitly asked.
Do not begin implementing the feature — this command only produces the spec.
