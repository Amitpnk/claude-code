# Rules: code style

Applies to `app/`. Enforced by `npm run lint` and `npm run format`; both must pass clean.

## Formatting — don't argue with Prettier

`.prettierrc` is the authority: semicolons on, double quotes, trailing commas everywhere,
100-column width. Run `npm run format` rather than hand-aligning. `eslint-config-prettier`
is last in `eslint.config.js`, so ESLint never reports formatting — a lint error is always
a real code issue.

## TypeScript

`tsconfig.json` sets `"strict": true`, targets ES2022, and emits CommonJS.

- No `any`. The one sanctioned exception is the `byPriorityThenCreatedAt` Drizzle order-by
  callback, which carries an explicit `eslint-disable-next-line`. Any new `any` needs the
  same explicit disable plus a reason — silent `any` is not acceptable.
- No non-null assertions (`!`) used to silence the compiler. Narrow the type instead:
  check for the value and throw a `NotFoundError` if it's missing.
- Unused variables are a warning only when prefixed with `_`
  (`argsIgnorePattern: "^_"`). Use `_req`, `_next` for genuinely unused Express params —
  that's why `app.ts` writes `(_req, res)`.
- Only `src/` is compiled (`include: ["src"]`). `tests/` is type-checked by vitest at run
  time, not by `npm run build`, so a type error in a test won't fail the build.

## Imports

- Relative paths, no path aliases — `../lib/errors`, `./db/schema`.
- Omit the `.ts` extension.
- Node builtins first, then npm packages, then local modules. Follow the existing order in
  `src/app.ts`.

## Naming

- Files: kebab-case (`task-priority.ts`, `projects.routes.ts`). Routers use the
  `<resource>.routes.ts` suffix.
- Exported validators: `parse<Thing>` (`parsePriority`). Exported constant lists:
  `SCREAMING_SNAKE` (`TASK_PRIORITIES`).
- Error classes: `<Reason>Error`, extending `AppError`.
- DB columns are `snake_case` in Postgres and `camelCase` in TypeScript — Drizzle maps
  them explicitly: `createdAt: timestamp("created_at")`.

## Comments

The codebase is deliberately comment-light. Write a comment only where the code cannot
explain itself — the `eslint-disable` on the ordering callback is the model. Don't add
comments that restate the line below them.

## What lint does not cover

`src/db/migrations/**`, `dist/**`, and `node_modules/**` are ignored in
`eslint.config.js`. A clean lint run says nothing about generated migrations — review
those by reading the SQL (see [database.md](database.md)).
