# Commit conventions for this repo

Read this when picking a type, when a change resists a single scope, or when
deciding whether something is one commit or several.

## Types

| Type | Use it when | Not when |
|---|---|---|
| `feat` | The app or the site can do something it could not before | You reorganised code that already worked — that is `refactor` |
| `fix` | Behaviour was wrong and now is right | You are adding a missing feature; nothing was broken |
| `docs` | Prose, slides, scripts, README, CLAUDE.md, rules | Code comments shipped with a code change — fold them into that commit |
| `refactor` | Same observable behaviour, different structure | Any behaviour changed at all, however small |
| `test` | Tests only | Tests that arrive with the feature they cover — that is one `feat` |
| `chore` | Config, tooling, housekeeping with no user-visible effect | Anything a reader of the changelog would want to know about |
| `perf` | Measurably faster, and you measured | You assume it is faster |
| `build` / `ci` | Dependencies, build config, workflows | — |
| `revert` | Undoing a previous commit; name it in the body | — |

`feat` and `fix` are the two that matter to a reader scanning history. When torn
between `fix` and `refactor`, ask whether a user could have filed a bug about the
old behaviour. If yes, `fix`.

A breaking change gets a `!` before the colon — `feat(routes)!: ...` — and the
body must open with `BREAKING CHANGE:` and say what callers have to do. In this
repo that mostly means a changed `/api/*` contract, since the tests call the API
with no credentials.

## Scopes

Three independent parts of the repo, and the scopes inside each:

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

The scope is where the *change lives*, not every file it touched. Adding a column
touches schema, routes, views and tests — the scope is `db`, because that is what
the change is about. A route fix that needed a schema tweak is `routes`.

Omit the scope entirely rather than inventing one. `chore: bump node to 22` is
better than a scope nobody else will ever use again. If a new scope genuinely
earns its place, add it to `SCOPES` in `check_message.py` **and** `RULES` in
`suggest_scope.py`, or the checker will reject the next commit that uses it.

## One commit or several

Split when the parts are independently revertable and independently interesting.
`suggest_scope.py` flags a change spanning app / site / config, which is the usual
sign. But do not split reflexively:

- Schema + API + view + test for one feature is **one** commit. Reverting half of
  it leaves the app broken, which is the definition of not independent.
- A drive-by formatting pass mixed into a bug fix is **two**. The fix is what
  someone will bisect to; noise around it costs them time.
- Ten slide decks edited in one pass is one `docs(slides)` commit, not ten.

Splitting means restaging, which means asking the user first. Never `git reset`
or `git stash` on your own initiative to reshape someone else's staged work.

## Trailers

After a blank line, at the end:

```
Refs: .claude/specs/01-login-logout.md
Closes: #12
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

Claude-authored commits carry the `Co-Authored-By` trailer. The checker skips
trailer lines when it enforces the 72-column wrap, so a long one is fine.

## Existing history

Most of this repo predates the convention: `feat: using seeds`, `Update
settings.json`, and one `feat: addint audit route skill`. Do not rewrite them —
published history is not worth the churn, and the series points viewers at
specific commits. Do not treat them as the pattern either. New commits follow
this file.
