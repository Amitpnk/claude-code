---
name: audit-routes
description: Audit TaskFlow's HTML and JSON route surfaces in app/ for drift and contract violations - validation that exists on one surface but not the other, inline error responses, unguarded id parsing, missing auth, duplicated helpers. Use for requests like "check the routes", "are the two surfaces in sync", "review app/src/app.ts", or before finishing any change that touches a route.
---

# Auditing the route surfaces

TaskFlow serves every resource operation from two places: form-post routes in
`app/src/app.ts` and JSON routes in `app/src/routes/projects.routes.ts` under `/api/*`.
They share a database layer but no code, so they drift. Per `.claude/rules/architecture.md`,
that drift is this codebase's most common defect.

Run the script first. It does the mechanical part in one pass and costs no context:

```bash
python .claude/skills/audit-routes/scripts/audit_routes.py
```

Exit code 0 means clean, 1 means findings. Each finding names a rule, a message and a
`file:line`.

## Then verify by hand

**The script is heuristic — it reads TypeScript as text.** Never report or fix a finding
without opening the cited line. It reasons about handler bodies by taking the text between
one route declaration and the next, so an unusual layout can mislead it, and it cannot see
anything a helper function does.

Two categories deserve particular scepticism:

- `architecture/dual-surface` "has no equivalent" findings are questions, not defects. A
  read-only page or a browser-only flow legitimately lives on one surface. Confirm intent
  before changing anything.
- A missing existence check on a delete may be deliberate on the HTML surface, where a
  redirect is friendlier than an error page. Say so rather than silently making both
  surfaces identical.

## Reporting

Group findings by severity, not by the rule name the script prints. Lead with what breaks
for a user — a 500 leaking a Postgres message outranks a duplicated helper. Give each one
a one-line fix and the file:line. `templates/audit-report.md` is the format.

State clearly whether you ran the test suite. It needs `docker compose up -d` and a
`SESSION_SECRET`; if Postgres is not running, say the findings are from reading the code.

## Fixing

`resources/route-contract.md` has the fix recipe for every rule the script emits. Read it
before editing — several fixes have a required shape (a shared `src/lib/` parser rather
than an inline check, for instance) and getting that wrong just moves the drift.

Fix only what you were asked to fix. A full audit of this repo currently returns around
17 findings; silently rewriting all of them is not a route change, it is a refactor. List
them, recommend an order, and let the user choose.

After any fix, from `app/`:

```bash
npm run lint && npm run test
```

Both must pass clean, and re-run the audit to confirm the finding is gone.
