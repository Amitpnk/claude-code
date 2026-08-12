---
name: commit-message
description: Write the commit message for a change in this repo - Conventional Commits type, the repo's scope vocabulary (app, db, routes, views, tests, docs, slides, skills, rules), an imperative subject, and a body that explains why. Use for requests like "commit this", "write a commit message", "what should this commit say", "squash these into one message" - and before any commit you are about to make yourself.
---

# Writing the commit message

A commit message is read months later by someone with no memory of the change, usually
while bisecting. That reader needs two things the diff cannot give them: what area moved,
and why.

This repo's history is a mix — `feat: using seeds`, `Update settings.json`, `feat: addint
audit route skill`. Do not copy the majority. New commits follow the convention below.
Do not rewrite the old ones either: the video series links to specific commits.

## 1. Read the change before naming it

Never write a subject from the conversation. Read what is actually staged:

```bash
git status --short
git diff --cached --stat
git diff --cached
```

If nothing is staged, the message describes the working tree instead — say so, and let the
user stage. **Do not run `git add -A` to make the diff match a message you already wrote.**

## 2. The shape

```
<type>(<scope>): <imperative subject, lowercase, no period, <=72 chars>

<Why this change exists: the symptom, the constraint, or the request behind it.
Wrap at 72. Two or three sentences is usually the whole body.>

<Anything the diff cannot explain: an approach rejected and why, a rule from
.claude/rules/ the change had to satisfy, a follow-up deliberately left out.>

<Optional trailers - Refs, Closes, Co-Authored-By - last, after a blank line.>
```

The subject completes the sentence **"this commit will ..."**. If it does not fit there, it
is not imperative yet.

## 3. Pick the type

| Type | Use it when | Not when |
|---|---|---|
| `feat` | The app or site can do something it could not before | You restructured code that already worked — that is `refactor` |
| `fix` | Behaviour was wrong and now is right | Nothing was broken; you are adding something missing |
| `docs` | Prose, slides, scripts, README, CLAUDE.md, rules | Comments shipped with a code change — fold into that commit |
| `refactor` | Same observable behaviour, different structure | Any behaviour changed at all |
| `test` | Tests only | Tests arriving with the feature they cover — one `feat` |
| `chore` | Config and housekeeping with no user-visible effect | A reader of the changelog would want to know |
| `perf` | Measurably faster, and you measured | You assume it is faster |
| `build` / `ci` | Dependencies, build config, workflows | — |
| `revert` | Undoing a commit; name it in the body | — |

Torn between `fix` and `refactor`? Ask whether a user could have filed a bug about the old
behaviour. If yes, `fix`.

Breaking changes get a `!` — `feat(routes)!: ...` — and the body opens with
`BREAKING CHANGE:` and says what callers must do. Here that mostly means a changed `/api/*`
contract, since the tests call the API with no credentials.

## 4. Pick the scope

Three independent parts of the repo:

| Area | Scope | Covers |
|---|---|---|
| app | `db` | `app/src/db/` — schema, migrations, seed |
| | `routes` | `app/src/routes/`, `app/src/app.ts` — either surface |
| | `views` | `app/src/views/`, `app/src/public/` |
| | `auth` | sessions, login/logout, middleware |
| | `tests` | `app/tests/` |
| | `deps` | `app/package.json` and the lockfile |
| | `app` | anything else under `app/` |
| site | `slides` | `docs/slides/` |
| | `scripts` | `docs/scripts/` — voiceover scripts |
| | `docs` | the rest of `docs/`, README |
| config | `skills`, `rules`, `commands`, `specs`, `plans` | the matching `.claude/` folder |
| | `claude` | `.claude/settings.json`, `CLAUDE.md`, anything else |

The scope is where the change *lives*, not every file it touched. Adding a column touches
schema, routes, views and tests — the scope is `db`, because that is what the change is
about. A route fix that needed a schema tweak is `routes`.

Omit the scope rather than invent one: `chore: bump node to 22` beats a scope nobody uses
again. A genuinely new scope must also be added to `SCOPES` in `scripts/check_message.py`,
or the checker rejects the next commit that uses it.

## 5. One commit or several

Split when the parts are independently revertable *and* independently interesting.

- Schema + API + view + test for one feature is **one** commit. Reverting half leaves the
  app broken, which is the definition of not independent.
- A formatting pass mixed into a bug fix is **two**. The fix is what someone bisects to.
- Ten decks edited in one pass is one `docs(slides)` commit, not ten.

`git diff --cached --name-only` spanning `app/`, `docs/` and `.claude/` at once is the usual
sign. Splitting means restaging, so ask first — never `git reset` or `git stash` on your own
initiative to reshape someone else's staged work.

## 6. Check it

```bash
python .claude/skills/commit-message/scripts/check_message.py -m "$(cat message.txt)"
```

Exit 0 is clean, 1 means findings. It catches the failures this repo actually has: gerund
subjects (`adding`), placeholder subjects (`Update <filename>`), a missing blank line before
the body, unwrapped body lines, unknown scopes.

**It reads text, not intent.** It cannot tell whether `feat` was the right type or whether
the body is true. A clean run means well-formed, not accurate.

## Examples

```
fix(routes): reject a non-numeric project id before the query

Number(req.params.id) yields NaN for /projects/abc, which reached Drizzle and
surfaced as a 500 with a raw Postgres message. Both surfaces now parse the id
through parseId in src/lib/, which throws ValidationError.

Shared in src/lib/ rather than fixed twice, per .claude/rules/architecture.md:
duplicating the check is how the two surfaces drift.
```

```
feat(db): add a due date to tasks

Tasks had no way to express when they were needed, so the dashboard could not
order by urgency. Adds a nullable due_date column, exposes it on both route
surfaces, and renders it in the task list.

Nullable rather than defaulted: a task with no deadline is the common case, and
a synthetic default would sort ahead of real ones.

Refs: .claude/specs/01-login-logout.md
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

The subject carries the whole change, so no body:

```
docs(slides): fix the episode number on deck 11
```

**Not** in the body: a list of changed files (`git show --stat` does it better and stays
true), a longer restatement of the subject, test output, or "as requested" — the reader does
not know which conversation that was.

## Committing — ask first

Write the message and show it. **Commit only when the user asked you to commit.** "Write a
commit message" is not that request.

When you do commit:

- **Check the branch first.** `git branch --show-current` — if it is `main`, branch before
  committing.
- Use a heredoc so the body survives:

  ```bash
  git commit -F - <<'EOF'
  feat(skills): add a commit-message skill
  ...
  EOF
  ```

- End with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Do not `--amend` a commit you did not create in this session, and do not push unless asked.

If a hook rejects the commit, fix the cause. Never reach for `--no-verify`.
