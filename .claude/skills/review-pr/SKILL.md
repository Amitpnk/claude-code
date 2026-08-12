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
gh pr view 12 --json title,body,author,baseRefName,headRefName    # what it claims to do
gh pr diff 12
```

For a local branch, `git diff main...HEAD` — three dots, so you see the branch's own work
and not everything that landed on `main` since. Also read the commits: `git log --oneline
main..HEAD`. A branch whose commits contradict its PR description is itself a finding.

**Read the description before the diff, then judge the diff against it.** The most valuable
finding in a review is usually "this does something the description does not mention".

## 2. Route each area to its rules

```bash
python .claude/skills/review-pr/scripts/review_scope.py --pr 12
python .claude/skills/review-pr/scripts/review_scope.py          # current branch vs main
```

It classifies every changed file, prints the rules file that governs it, the checker to run,
and what to look at by hand. Costs no context and stops you reviewing a migration against
the wrong standard.

Run the checkers it names. They are the mechanical pass:

| Changed | Checker |
|---|---|
| `app/src/app.ts`, `app/src/routes/` | `audit-routes` — but see below |
| `app/src/db/seed.ts`, any enum or column | `seed-refresh` |
| `docs/slides/` | `new-episode-deck`'s `verify_deck.py` |

**`audit_routes.py` reports on the whole repo, not on the diff.** A full run currently
returns roughly 17 findings, most of them pre-existing. Attributing those to the PR author
is the single easiest way to make a review worthless. Check whether each finding's line is
in the diff — `git diff main...HEAD -- <file>` — and separate "this PR introduced it" from
"this already existed". Say which is which.

## 3. Read the diff yourself

`resources/review-checklist.md` is what to look for per area, keyed to the rules. The three
that catch the most here:

- **Dual-surface drift.** A mutation changed on one surface and not the other is this
  codebase's most common defect, per `.claude/rules/architecture.md`.
- **Migrations.** Not linted, never hand-editable, and `db:generate` can emit a destructive
  plan from an additive-looking edit. Read the SQL.
- **Tests that pass for the wrong reason.** The suite shares one database and truncates
  once per file, so order matters and a new test can silently depend on a previous one.

## 4. Verify before you claim

Run what you can, from `app/`:

```bash
npm run lint && npm run test        # needs docker compose up -d
```

If Postgres is not up, say the review is from reading the code and that the suite did not
run. Never imply a test result you did not see. If you cannot verify a claim, mark it as a
question rather than a finding.

## Reporting

`templates/pr-review.md` is the format: blocking, should-fix, questions, nits, then a
verdict. Rules for it:

- Every finding gets a `file:line` and a one-line fix.
- **Separate pre-existing problems from what this PR introduced.** Under a heading, not in
  a parenthetical.
- Sort by what it costs a user, not by how easy it was to spot. A 500 leaking a Postgres
  message outranks any amount of duplication.
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
