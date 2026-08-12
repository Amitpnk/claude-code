---
name: commit-message
description: Write the commit message for a change in this repo - Conventional Commits type, the repo's scope vocabulary (app, db, routes, views, tests, docs, slides, skills, rules), an imperative subject, and a body that explains why. Use for requests like "commit this", "write a commit message", "what should this commit say", "squash these into one message" - and before any commit you are about to make yourself.
---

# Writing the commit message

A commit message is read months later by someone with no memory of the change, usually
while bisecting. That reader needs two things the diff cannot give them: what area moved,
and why. Everything below serves those two.

This repo's history is a mix — `feat: using seeds`, `Update settings.json`, `feat: addint
audit route skill`. Do not copy the majority. New commits follow the convention here.

## Read the change before naming it

Never write a subject from the conversation. Read what is actually staged:

```bash
git status --short
git diff --cached --stat
git diff --cached
```

If nothing is staged, the message describes the working tree instead — say so, and let the
user stage. **Do not run `git add -A` to make the diff match a message you already wrote.**

Then get the scope vocabulary and a split-commit check, which costs no context:

```bash
python .claude/skills/commit-message/scripts/suggest_scope.py
```

It maps the touched paths to this repo's scopes and warns when a change spans unrelated
areas. Its scope suggestion is a starting point, not a verdict — a change under
`app/src/db/` that exists to fix a route is `fix(routes)`, whatever the path says.

## The shape

```
<type>(<scope>): <imperative subject, lowercase, no period, <=72>

<why, wrapped at 72 - what was wrong or missing, and what the reader
would otherwise wonder about this diff>
```

`templates/commit-message.md` has the full form with worked examples for this repo.
`resources/commit-conventions.md` is the type and scope vocabulary and the judgement calls —
read it when picking between `feat` and `refactor`, or when a change resists one scope.

## Check it

```bash
python .claude/skills/commit-message/scripts/check_message.py -m "$(cat message.txt)"
```

Exit 0 is clean, 1 means findings. It catches the failures this repo actually has: gerund
subjects (`adding`, `updating`), placeholder subjects (`Update <filename>`), a missing blank
line before the body, unwrapped body lines, and unknown scopes.

**It reads text, not intent.** It cannot tell whether `feat` was the right type or whether
the body is true. A clean run means the message is well-formed, not that it is accurate.

## The body is not optional padding

Omit it only when the subject genuinely says everything — a typo fix, a version bump.
For anything else, write the sentence the diff cannot: the constraint, the bug's symptom,
the reason the obvious approach was not taken. Do not list the files; `git show` does that
better than prose.

## Committing — ask first

Write the message and show it. **Commit only when the user asked you to commit.** "Write a
commit message" is not that request.

When you do commit:

- **Check the branch first.** `git branch --show-current` — if it is `main`, branch before
  committing.
- Use a heredoc for the message so the body survives:

  ```bash
  git commit -F - <<'EOF'
  feat(skills): add a commit-message skill
  ...
  EOF
  ```

- End the message with the co-author trailer:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- Do not `--amend` a commit you did not create in this session, and do not push unless asked.

If a hook rejects the commit, fix the cause. Never reach for `--no-verify`.
