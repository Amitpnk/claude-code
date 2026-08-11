# `.claude/`

Everything in this folder configures how Claude Code behaves in this repo. Each subfolder
is loaded by a different mechanism, at a different time — that distinction is the whole
point of the layout, so it's worth knowing which is which.

| Path | Loaded | By what |
|---|---|---|
| `settings.json` | every session | Claude Code, automatically. Team-shared, committed. |
| `settings.local.json` | every session | Same, but personal. Gitignored — create it yourself if you want local overrides. |
| `commands/` | on invocation | You type `/create-spec …`. Nothing loads until then. |
| `skills/` | on match | Claude picks a skill when the request matches its `description`, or you name it. |
| `rules/` | on demand | **Not** auto-loaded. Read only when something points at it — see below. |
| `specs/` | on demand | Project content, not config. Written by `/create-spec`, read when implementing. |
| `plans/` | on demand | Written by Plan Mode because `settings.json` points it here. Read when implementing. |

Note the root [`CLAUDE.md`](../CLAUDE.md) and [`app/CLAUDE.md`](../app/CLAUDE.md) are the
only files loaded into *every* session automatically. Everything here is either explicitly
invoked or explicitly referenced.

## `settings.json`

Permissions shared by everyone working in this repo: an allowlist of read-only commands
that shouldn't need a prompt (`npm run lint`, `git diff`, …) and a denylist for `.env`
files so secrets are never read into context. `.env.example` stays readable on purpose.

It also sets `"plansDirectory": ".claude/plans"` so Plan Mode writes into this repo instead
of the global default — see [`plans/`](#plans) below.

Personal overrides go in `settings.local.json`, which is gitignored. Later sources win:
`~/.claude/settings.json` → `.claude/settings.json` → `.claude/settings.local.json`.

## `commands/`

One markdown file per slash command. Frontmatter declares `description`, `argument-hint`,
and `allowed-tools`; the body is the prompt, with `$ARGUMENTS` substituted in.

- [`create-spec.md`](commands/create-spec.md) — `/create-spec <feature>` creates a feature
  branch and writes a full spec to `specs/`. It does not implement anything.

## `skills/`

One folder per skill, each containing a `SKILL.md` whose frontmatter `name` matches the
folder name. The `description` is what Claude matches against, so it should name the
trigger phrases, not just the topic.

- [`add-task-field/`](skills/add-task-field/SKILL.md) — the correct order for adding a
  column to `tasks`/`projects`: schema → migration → API → view → seed → test → verify.
- [`audit-routes/`](skills/audit-routes/SKILL.md) — check the HTML and `/api/*` surfaces in
  `app/` for drift: validation on one surface but not the other, inline error responses,
  unguarded id parsing, duplicated helpers.
- [`new-episode-deck/`](skills/new-episode-deck/SKILL.md) — build or check a slide deck in
  `docs/slides/`. Scaffolds from the house template, then validates numbering, tag balance
  and image refs.

`add-task-field` and `audit-routes` make a matched pair worth demoing together — one builds,
the other checks what was built. Neither knows about the other; Claude picks whichever the
request matches.

A skill can be a single `SKILL.md`, or a folder with supporting files beside it. The last
two are the full shape, and each part loads at a different moment:

```
audit-routes/
├── SKILL.md                  the workflow — read when the skill triggers
├── scripts/
│   └── audit_routes.py       runs; never read into context
├── templates/
│   └── audit-report.md       the report format
└── resources/
    └── route-contract.md     fix recipes — read only when actually fixing
```

That is progressive disclosure: the `description` above is always in context, `SKILL.md` is
read only when a request matches it, and `route-contract.md` only if a fix is actually being
written. A script is cheaper still — running it costs no context at all, which is why the
detection logic lives in Python rather than as prose Claude has to apply by hand.
`new-episode-deck/` follows the same layout, with two scripts (`new_deck.py`,
`verify_deck.py`), the deck skeleton in `templates/`, and the CSS component catalog in
`resources/`.

## `rules/`

Topic-scoped constraints, kept out of `CLAUDE.md` so they load only when relevant. Nothing
reads these automatically — they reach Claude because `commands/create-spec.md` names them
in its research step, or because you `@`-mention one in a prompt.

- [`architecture.md`](rules/architecture.md) — dual route surface, error handling, shared validation
- [`api-style.md`](rules/api-style.md) — the HTTP contract for `/api/*`: paths, status codes, body shapes
- [`database.md`](rules/database.md) — schema-to-migration workflow, enum and relation conventions
- [`code-style.md`](rules/code-style.md) — Prettier/ESLint boundaries, strict-TS rules, naming
- [`testing.md`](rules/testing.md) — the shared-database traps in the test suite

Keep these as *rules* — things a change can violate. Descriptive explanation of how the
app works belongs in `app/CLAUDE.md`, which is always loaded.

## `specs/`

Feature specs, numbered and kebab-cased (`01-login-logout.md`). Output of `/create-spec`,
input to Plan Mode. These are project artifacts rather than configuration — Claude Code
has no built-in meaning for this folder.

## `plans/`

Implementation plans, named to match the spec they come from (`01-login-logout.md` here
mirrors `specs/01-login-logout.md`). A spec says *what* and *why*; the plan says *how* and
*in what order*.

Unlike `specs/`, this folder **is** known to Claude Code — but only because
`settings.json` sets `plansDirectory` to it. Without that key, approving a plan writes to
`~/.claude/plans/` instead, outside the repo. Asking for a path in your prompt does not
change this: the harness writes the plan artifact itself and reads only the setting.

Plans are committed, like specs. Episodes 08 and 09 point viewers at
`.claude/plans/01-login-logout.md`, so it has to exist here.

Changing `plansDirectory` takes effect on the next session — or after opening `/hooks`
once, which reloads config.
