# Commit message template

Copy the shape, not the words. Everything in angle brackets is yours to write.

```
<type>(<scope>): <imperative, lowercase, no trailing period, <=72 chars>

<Why this change exists: the symptom, the constraint, or the request behind it.
Wrap at 72. Two or three sentences is usually the whole body.>

<Anything the diff cannot explain: an approach rejected and why, a follow-up
deliberately left out, a rule from .claude/rules/ the change had to satisfy.>

<Optional trailers - Refs, Closes, Co-Authored-By - last, after a blank line.>
```

The subject completes the sentence **"this commit will ..."**. If it does not fit
there, it is not imperative yet.

## Worked examples from this repo

A defect, both surfaces, with the reason the fix lives where it does:

```
fix(routes): reject a non-numeric project id before the query

Number(req.params.id) yields NaN for /projects/abc, which reached Drizzle
and surfaced as a 500 with a raw Postgres message. Both surfaces now parse
the id through parseId in src/lib/, which throws ValidationError.

Shared in src/lib/ rather than fixed twice, per .claude/rules/architecture.md:
duplicating the check is how the two surfaces drift.
```

A feature that spans schema, API, view and tests — one commit, because they are
one change:

```
feat(db): add a due date to tasks

Tasks had no way to express when they were needed, so the dashboard could not
order by urgency. Adds a nullable due_date column, exposes it on both route
surfaces, and renders it in the task list.

Nullable rather than defaulted: a task with no deadline is the common case,
and a synthetic default would sort ahead of real ones.
```

A subject that carries the whole change, so no body:

```
docs(slides): fix the episode number on deck 11
```

A change to the tooling in `.claude/`:

```
feat(skills): add a commit-message skill

Commit subjects in this repo drifted between "feat: adding X" and "Update
file.html", so history reads as a list of touched files rather than a record
of decisions. The skill fixes the convention and ships a checker for it.
```

## What does not belong in the body

- A list of the files changed. `git show --stat` does it better and stays true.
- A restatement of the subject in longer words.
- Test output, tool logs, or the transcript of how the change was arrived at.
- "As requested" — the reader does not know which conversation that was.
