#!/usr/bin/env python3
"""Map the files in a change to this repo's commit scopes, and flag a change
that should probably be more than one commit.

Reads the staged diff. With nothing staged it falls back to the working tree
(tracked modifications plus untracked files) and says so.

The scope it prints comes from paths alone. A change under app/src/db/ that
exists to fix a route is fix(routes), whatever the path says - the suggestion
is a starting point, not a verdict.

  python .claude/skills/commit-message/scripts/suggest_scope.py
"""
import argparse
import os
import subprocess
import sys

# Ordered: first match wins, so specific paths precede the general ones.
# Kept in sync with SCOPES in scripts/check_message.py.
RULES = [
    ("app/tests/", "tests"),
    ("app/src/db/", "db"),
    ("app/src/routes/", "routes"),
    ("app/src/app.ts", "routes"),
    ("app/src/views/", "views"),
    ("app/src/public/", "views"),
    ("app/src/middleware/", "auth"),
    ("app/package.json", "deps"),
    ("app/package-lock.json", "deps"),
    ("app/", "app"),
    ("docs/slides/", "slides"),
    ("docs/scripts/", "scripts"),
    ("docs/", "docs"),
    (".claude/skills/", "skills"),
    (".claude/rules/", "rules"),
    (".claude/commands/", "commands"),
    (".claude/specs/", "specs"),
    (".claude/plans/", "plans"),
    (".claude/", "claude"),
    ("CLAUDE.md", "claude"),
    ("README.md", "docs"),
]

# Areas that rarely belong in one commit together: the site, the demo app, and
# the Claude Code configuration are independent parts of this repo.
AREAS = {
    "tests": "app",
    "db": "app",
    "routes": "app",
    "views": "app",
    "auth": "app",
    "deps": "app",
    "app": "app",
    "slides": "site",
    "scripts": "site",
    "docs": "site",
    "skills": "config",
    "rules": "config",
    "commands": "config",
    "specs": "config",
    "plans": "config",
    "claude": "config",
}

TYPE_HINTS = [
    ("tests", "test - unless the tests come with the feature they cover"),
    ("db", "feat for a new column, fix for a bad migration"),
    ("docs", "docs"),
    ("slides", "docs, or feat for a deck that did not exist"),
    ("deps", "build or chore"),
]


def git(args, repo_root):
    result = subprocess.run(
        ["git"] + args, cwd=repo_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode("utf-8", "replace"))
        sys.exit(2)
    return [
        line.strip()
        for line in result.stdout.decode("utf-8", "replace").splitlines()
        if line.strip()
    ]


def collect(repo_root):
    staged = git(["diff", "--cached", "--name-only"], repo_root)
    if staged:
        return staged, "staged"
    working = git(["diff", "--name-only"], repo_root)
    untracked = git(["ls-files", "--others", "--exclude-standard"], repo_root)
    return sorted(set(working + untracked)), "working tree (nothing is staged)"


def scope_for(path):
    normalised = path.replace("\\", "/")
    for prefix, scope in RULES:
        if normalised.startswith(prefix):
            return scope
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument(
        "--repo-root", default=os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    )
    args = parser.parse_args()

    files, source = collect(args.repo_root)
    if not files:
        print("suggest-scope: no changes - nothing to describe.")
        return 0

    by_scope = {}
    unmapped = []
    for path in files:
        scope = scope_for(path)
        if scope is None:
            unmapped.append(path)
        else:
            by_scope.setdefault(scope, []).append(path)

    print("Reading the {0}: {1} file(s)\n".format(source, len(files)))

    ranked = sorted(by_scope.items(), key=lambda item: (-len(item[1]), item[0]))
    for scope, paths in ranked:
        print("  {0:<9} {1} file(s)".format(scope, len(paths)))
        for path in paths[:4]:
            print("            {0}".format(path))
        if len(paths) > 4:
            print("            ... and {0} more".format(len(paths) - 4))
    if unmapped:
        print("  {0:<9} {1} file(s) - pick a scope by hand".format("(none)", len(unmapped)))
        for path in unmapped[:4]:
            print("            {0}".format(path))
    print("")

    if ranked:
        primary = ranked[0][0]
        print("Suggested scope: {0}".format(primary))
        for scope, hint in TYPE_HINTS:
            if scope == primary:
                print("Type usually:    {0}".format(hint))
                break
        else:
            print("Type usually:    feat for new behaviour, fix for a defect, refactor for neither")
        print("")

    areas = set(AREAS.get(scope, "other") for scope in by_scope)
    if len(areas) > 1:
        print(
            "SPLIT? This change spans {0} unrelated areas of the repo ({1}).".format(
                len(areas), ", ".join(sorted(areas))
            )
        )
        print("       One commit per area reads better and reverts cleanly. Ask before")
        print("       splitting - the user may have meant them as one change.")
        return 1

    print("One area - one commit is right.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
