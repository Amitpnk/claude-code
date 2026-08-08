# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TaskFlow — a small team task/project tracker. It's the companion demo app for the
[Learn Claude Code the Right Way](../README.md) video series, used on-camera to demonstrate
CLAUDE.md, Skills, SubAgents, Spec-Driven Development, Plan Mode, MCP, and Hooks. Despite the
teaching purpose, treat it as a real, evolving codebase — changes should be correct and tested.

Stack: Node.js 20, TypeScript, Express + EJS (server-rendered views), PostgreSQL 16 + Drizzle ORM, vitest + supertest.

## Commands

All commands run from `app/`.

```bash
cp .env.example .env
docker compose up -d       # local Postgres on :5432
npm install
npm run db:generate        # generate SQL migrations from src/db/schema.ts
npm run db:migrate         # apply migrations
npm run db:seed            # sample projects + tasks
npm run dev                # tsx watch, http://localhost:3000
```

| Command | Purpose |
|---|---|
| `npm run dev` | Dev server with reload (tsx watch) |
| `npm run build` | Compile TypeScript to `dist/` |
| `npm start` | Run the compiled build |
| `npm run test` | Run vitest + supertest against the real DB |
| `npm run lint` | ESLint |
| `npm run format` | Prettier |

Run a single test file: `npx vitest run tests/projects.test.ts`. Run by name: `npx vitest run -t "rejects a project without a name"`.

Tests hit the real Postgres database configured by `DATABASE_URL` (no mocking) — Postgres must be
running (`docker compose up -d`) before `npm run test`. `tests/projects.test.ts` truncates the
`projects`/`tasks` tables in `beforeAll`, so tests share and reset that state.

## Architecture

**Two parallel route surfaces share the same DB layer**: server-rendered HTML routes live directly
in `src/app.ts` (e.g. `POST /projects/:id/tasks` reads a form body and `res.redirect`s back to the
page), while the JSON API lives in `src/routes/projects.routes.ts` mounted at `/api/*` (same
operations, `res.json`/status codes, thrown `AppError`s instead of rendered error pages). When
adding an operation, decide whether it needs both surfaces or just one, and keep validation
(e.g. `parsePriority`) shared between them via a helper in `src/lib/` rather than duplicated.

**Error handling**: routes throw subclasses of `AppError` (`src/lib/errors.ts` — `NotFoundError` →
404, `ValidationError` → 400) and always delegate to `next(err)`, never handle errors inline. The
single error middleware at the bottom of `src/app.ts` inspects `req.path`: `/api/*` requests get a
JSON error body, everything else gets the rendered `error.ejs` view.

**Schema → migration workflow** (`src/db/schema.ts` + `drizzle-kit`): the schema file is the source
of truth. After changing it, run `npm run db:generate` to produce a SQL file under
`src/db/migrations/`, review the generated SQL, then `npm run db:migrate` to apply it. Never
hand-edit a generated migration file — change the schema and regenerate instead. Migrations are
excluded from ESLint (`eslint.config.js` ignores `src/db/migrations/**`).

**Data model** (`src/db/schema.ts`): `projects` 1—many `tasks` (cascade delete). `tasks.status` and
`tasks.priority` are Postgres enums (`taskStatus`, `taskPriority`) with defaults (`todo`,
`medium`) — follow this pgEnum + `.default(...)` pattern for new fixed-value fields. Tasks are
conventionally listed ordered by priority (high → low) then creation time; see the
`byPriorityThenCreatedAt` helper duplicated in both `src/app.ts` and
`src/routes/projects.routes.ts`.

**Views** (`src/views/*.ejs` + `src/views/partials/`): plain server-rendered EJS, no client-side
framework. Status/priority are rendered as `<span class="…-badge …-badge--<value>">` — matching
CSS lives in `src/public/styles.css`.

**Adding a field to `tasks`/`projects`**: use the `add-task-field` skill (`.claude/skills/add-task-field/`)
— it encodes the required order (schema → migration → API → view → seed → test → lint/test) for
touching this codebase's DB layer safely.
