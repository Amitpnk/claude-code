---
name: review-pr
description: Review a pull request or a feature branch against this repo's rules before it merges - dual-surface drift, migration safety, seed coverage, test gaps, deck and docs consistency. Use for requests like "review PR 12", "review this branch", "check my changes before I push", "is this ready to merge". Routes each changed area to the rules file and checker that governs it.
---

# Reviewing a change before it merges

This repo already encodes its standards in `.claude/rules/` and in three checker scripts.
A review here is not a fresh opinion about the code — it is holding the diff against those
rules and saying what fails. Anything you flag should trace back to a rule file or to
observable breakage.

For generic correctness bugs — logic errors, races, unhandled cases — `/code-review` is the
better tool and knows nothing about this repo. This skill covers the conventions
`/code-review` cannot see. Running both on a substantial PR is reasonable.

## 1. Get the diff

```bash
gh pr view 12 --json title,body,author,baseRefName,headRefName   # what it claims to do
gh pr diff 12
gh pr diff 12 --name-only                                        # to route it, below
```

For a local branch, `git diff main...HEAD` — three dots, so you see the branch's own work
and not everything that landed on `main` since. `git diff --name-only main...HEAD` gives the
file list. To review a branch without checking it out: `git diff --name-only main...origin/the-branch`.

Also read the commits: `git log --oneline main..HEAD`. A branch whose commits contradict its
PR description is itself a finding.

**Read the description before the diff, then judge the diff against it.** The most valuable
finding in a review is usually "this does something the description does not mention".

## 2. Route each changed area to its rules

Match the file list against this table and read only the rows that apply.

| Changed paths | Rules | Checker |
|---|---|---|
| `app/src/db/migrations/` | `database.md` | none — **read the SQL** |
| `app/src/db/` (schema, seed) | `database.md` | `seed-refresh/scripts/check_seed.py` |
| `app/src/routes/`, `app/src/app.ts` | `architecture.md`, `api-style.md` | `audit-routes/scripts/audit_routes.py` |
| `app/src/views/`, `app/src/public/` | `architecture.md` | none |
| `app/src/middleware/`, session/auth libs | `api-style.md`, `specs/01-login-logout.md` | none |
| `app/tests/` | `testing.md` | none |
| `app/` (anything else) | `code-style.md` | `npm run lint` |
| `docs/slides/` | — | `new-episode-deck/scripts/verify_deck.py <deck>` |
| `docs/`, `README.md` | — | none |
| `.claude/`, `CLAUDE.md` | `.claude/README.md` | none |

Rules files are in `.claude/rules/`. Review in that order too — schema before the code that
queries it, views before the tests that assert on them.

**Always look twice at these, whatever else the PR does:**

- `app/src/db/migrations/*.sql` — generated, never linted, and a drop-and-recreate loses data.
- `app/src/db/schema.ts` — a schema change with no migration in the same PR will not deploy.
- `.claude/settings.json` — a new `allow` entry binds everyone who clones the repo.
- `.env.example` — confirm no real secret landed in it.
- `app/package.json` — confirm the lockfile came with it.

### The audit-routes caveat

**`audit_routes.py` reports on the whole repo, not on the diff.** A full run currently
returns roughly 17 findings, most of them pre-existing. Attributing those to the PR author
is the single easiest way to make a review worthless. Check whether each finding's line is
in the diff — `git diff main...HEAD -- <file>` — and separate "this PR introduced it" from
"this already existed". Say which is which.

## 3. Read the diff yourself

`resources/review-checklist.md` is what to look for per area, keyed to the rules. Read the
sections the table above pointed you at. The three that catch the most here:

- **Dual-surface drift.** A mutation changed on one surface and not the other is this
  codebase's most common defect, per `.claude/rules/architecture.md`.
- **Migrations.** `db:generate` can emit a destructive plan from an additive-looking edit.
- **Tests that pass for the wrong reason.** The suite shares one database and truncates once
  per file, so order matters and a new test can silently depend on a previous one.

## 4. Verify before you claim

From `app/`:

```bash
npm run lint && npm run test        # needs docker compose up -d
```

If Postgres is not up, say the review is from reading the code and that the suite did not
run. Never imply a test result you did not see. If you cannot verify a claim, mark it a
question rather than a finding.

## 5. Report

Four sections, then a verdict:

```markdown
## Blocking
<Merging breaks something a user hits, loses data, or leaks internals.
Leave empty when it is empty — do not pad it.>

- **A non-numeric project id returns 500 with a raw Postgres message.**
  `Number(req.params.id)` yields `NaN` and reaches the query. Parse through a
  `parseId` in `src/lib/` and throw `ValidationError`.
  `app/src/routes/projects.routes.ts:43`

## Should fix before merge
<Real defects that are not emergencies: surface drift, missing test cases, a
seed that leaves a new branch unreachable.>

## Questions
<Looks wrong but may be deliberate. Ask; do not assert.>

## Nits
<Naming, duplication, anything the linter misses. Label as optional.>

## Pre-existing — not from this PR
<What the checkers reported that the diff did not introduce. Keeping this
separate is what makes the sections above trustworthy.>

## Verdict
<ready to merge / ready once the blocking items are fixed / needs a
conversation about approach — then the shortest path to green.>
```

Rules for it:

- Every finding gets a `file:line` and a one-line fix.
- Sort by what it costs a user, not by how easy it was to spot. A 500 leaking a Postgres
  message outranks any amount of duplication.
- Open with one sentence on what the change does *in your words*. If you cannot write that
  sentence, it is the first finding.
- State what you ran. "Read the code only; Postgres was not up" is a fine answer.
- If the change is fine, say so plainly. A review that manufactures findings to look
  thorough trains people to ignore reviews.

## What not to do

- **Do not fix what you are reviewing** unless asked. A review the author cannot read as a
  diff of their own work is not a review. List, recommend an order, stop.
- **Do not post to GitHub unprompted.** `gh pr review`, `gh pr comment` and `gh pr merge`
  are public, attributed to the user, and `--approve` is a claim in their name. Show the
  review and ask.
- **Do not approve or merge on the user's behalf**, even when they say the review looks
  good — that is a separate instruction to give.
