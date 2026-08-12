#!/usr/bin/env python3
"""Route the files in a pull request to the rules and checkers that govern them.

A review of this repo is not a fresh opinion - it is holding the diff against
.claude/rules/. This prints, per area of the change: the rules file, the checker
to run, and what to read by hand. It does not read the diff's contents.

  python .claude/skills/review-pr/scripts/review_scope.py            # branch vs main
  python .claude/skills/review-pr/scripts/review_scope.py --pr 12    # a GitHub PR
  python .claude/skills/review-pr/scripts/review_scope.py --base lab
"""
import argparse
import os
import subprocess
import sys

# (key, label, path prefixes, rules, checker command, hand-review focus)
# Ordered: first match wins, so specific paths precede general ones.
AREAS = [
    (
        "migrations",
        "database migrations",
        ["app/src/db/migrations/"],
        [".claude/rules/database.md"],
        None,
        [
            "Read the SQL. ESLint ignores this folder, so a clean lint says nothing.",
            "A column drop/recreate loses data - check db:generate did not emit one",
            "  from an edit that looked additive.",
            "Hand-edited migrations are forbidden: the diff to schema.ts must explain",
            "  every statement here.",
        ],
    ),
    (
        "db",
        "schema and seed",
        ["app/src/db/"],
        [".claude/rules/database.md"],
        "python .claude/skills/seed-refresh/scripts/check_seed.py",
        [
            "New enum value or column? The seed must exercise it, and every view",
            "  branch that reads it must have data reaching it.",
            "Enum columns need .notNull().default(...) so existing rows survive.",
            "Child rows need onDelete: 'cascade' and a relations(...) block.",
            "A schema change with no migration in the same PR will not deploy.",
        ],
    ),
    (
        "routes",
        "route surfaces",
        ["app/src/routes/", "app/src/app.ts"],
        [".claude/rules/architecture.md", ".claude/rules/api-style.md"],
        "python .claude/skills/audit-routes/scripts/audit_routes.py",
        [
            "Did both surfaces change together? HTML in app.ts, JSON in routes/.",
            "Handlers throw AppError and forward with next(err) - no inline",
            "  res.status(4xx) even when the output looks identical.",
            "Validate input, then check the parent exists, then write. That order",
            "  decides whether a bad body on a missing parent is 400 or 404.",
            "Shared validation belongs in app/src/lib/, imported by both surfaces.",
            "NOTE: audit_routes.py scans the whole repo. Most findings predate this",
            "  PR - check each cited line is actually in the diff before reporting it.",
        ],
    ),
    (
        "views",
        "views and styles",
        ["app/src/views/", "app/src/public/"],
        [".claude/rules/architecture.md"],
        None,
        [
            "Enum fields render as <span class='<field>-badge <field>-badge--<value>'>",
            "  with matching CSS. A new value needs a new rule or it renders unstyled.",
            "Every template uses partials/header and partials/footer.",
            "Server-rendered EJS only - no client framework, no build step.",
            "Does the empty state exist? Zero rows, one row, many.",
        ],
    ),
    (
        "auth",
        "sessions and auth",
        ["app/src/middleware/", "app/src/lib/session", "app/src/lib/auth"],
        [".claude/rules/api-style.md", ".claude/specs/01-login-logout.md"],
        None,
        [
            "/api/* is unauthenticated by design. Anything changing that must say",
            "  what happens to the tests, which call the API with no credentials.",
            "No secrets in source. New config comes from .env and .env.example.",
        ],
    ),
    (
        "tests",
        "tests",
        ["app/tests/"],
        [".claude/rules/testing.md"],
        None,
        [
            "The suite runs against a real Postgres and TRUNCATEs once per file,",
            "  not per test - a new test may pass only because of an earlier one.",
            "A new test file needs its own afterAll(pool.end) or the run hangs.",
            "Assert the status code AND the body shape.",
            "A new field needs three cases: default applied, valid accepted,",
            "  invalid rejected with 400.",
        ],
    ),
    (
        "deps",
        "dependencies",
        ["app/package.json", "app/package-lock.json"],
        [],
        None,
        [
            "Is the lockfile in the same commit as package.json?",
            "Does anything in the diff actually use the new dependency?",
        ],
    ),
    (
        "app",
        "app (other)",
        ["app/"],
        [".claude/rules/code-style.md"],
        None,
        [
            "Strict TypeScript: no any, no ! to silence the compiler.",
            "Relative imports, no .ts extension, builtins then packages then local.",
            "Comment-light by design - a comment must say what the code cannot.",
        ],
    ),
    (
        "slides",
        "slide decks",
        ["docs/slides/"],
        [],
        "python .claude/skills/new-episode-deck/scripts/verify_deck.py <deck>",
        [
            "Number and title must match the videos array in docs/index.html.",
            "Slide counter, progress bar and <!-- SLIDE n --> comments stay in step.",
            "Closing slide points at the next episode.",
        ],
    ),
    (
        "scripts",
        "voiceover scripts",
        ["docs/scripts/"],
        [],
        None,
        ["Mirrors its deck slide by slide, with timestamps."],
    ),
    (
        "docs",
        "site and docs",
        ["docs/", "README.md"],
        [],
        None,
        [
            "An episode going live needs status, youtube, article and slides set",
            "  together in docs/index.html - a live entry with a dead link is worse",
            "  than one still marked upcoming.",
        ],
    ),
    (
        "config",
        "Claude Code config",
        [".claude/", "CLAUDE.md"],
        [".claude/README.md"],
        None,
        [
            "A new permission in settings.json applies to everyone - is it read-only?",
            "A skill's description is what triggers it: does it name the phrases",
            "  someone would actually type?",
            "A new rule belongs in rules/ only if a change can violate it;",
            "  explanation belongs in app/CLAUDE.md.",
        ],
    ),
]

# Paths that deserve a second look whatever else the PR does.
# (prefix, why, required suffix or None). Keep this section short - a HIGH RISK
# list padded with Drizzle bookkeeping is one nobody reads.
HIGH_RISK = [
    ("app/src/db/migrations/", "generated SQL, never linted - read every statement", ".sql"),
    ("app/src/db/schema.ts", "schema change - confirm a matching migration is included", None),
    (".claude/settings.json", "shared permissions - a new allow entry binds everyone", None),
    (".env.example", "config surface - confirm no real secret landed in it", None),
    ("app/package.json", "dependency change - confirm the lockfile came with it", None),
]

REVIEW_ORDER = [
    "migrations",
    "db",
    "routes",
    "auth",
    "views",
    "tests",
    "deps",
    "app",
    "slides",
    "scripts",
    "docs",
    "config",
]


def run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = result.stdout.decode("utf-8", "replace")
    err = result.stderr.decode("utf-8", "replace")
    return result.returncode, out, err


def collect(repo_root, pr, base, head):
    """(files, description) for the change under review."""
    if pr:
        code, out, err = run(["gh", "pr", "diff", str(pr), "--name-only"], repo_root)
        if code != 0:
            sys.stderr.write(err or "gh pr diff failed\n")
            sys.exit(2)
        return [line.strip() for line in out.splitlines() if line.strip()], "PR #" + str(pr)

    for ref in (base, head):
        code, _, _ = run(["git", "rev-parse", "--verify", "--quiet", ref], repo_root)
        if code != 0:
            sys.stderr.write("ref '" + ref + "' does not exist\n")
            sys.exit(2)

    if head == "HEAD":
        code, out, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root)
        label = out.strip() if code == 0 else "HEAD"
    else:
        label = head

    # Three dots: the branch's own work, not what landed on the base since.
    code, out, _ = run(["git", "diff", "--name-only", base + "..." + head], repo_root)
    files = [line.strip() for line in out.splitlines() if line.strip()]
    if files:
        _, log, _ = run(["git", "log", "--oneline", base + ".." + head], repo_root)
        commits = len([line for line in log.splitlines() if line.strip()])
        return files, "branch {0} vs {1} - {2} commit(s)".format(label, base, commits)

    if head != "HEAD":
        return [], "{0} has no changes against {1}".format(label, base)

    # On the base branch itself, or nothing merged yet: review what is uncommitted.
    _, out, _ = run(["git", "diff", "--name-only", "HEAD"], repo_root)
    _, untracked, _ = run(["git", "ls-files", "--others", "--exclude-standard"], repo_root)
    files = sorted(set(out.split() + untracked.split()))
    return files, "uncommitted work on {0} (nothing differs from {1})".format(label, base)


def area_for(path):
    normalised = path.replace("\\", "/")
    for key, _, prefixes, _, _, _ in AREAS:
        for prefix in prefixes:
            if normalised.startswith(prefix):
                return key
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument("--pr", help="GitHub PR number (uses gh)")
    parser.add_argument("--base", default="main", help="base ref for a local branch")
    parser.add_argument(
        "--head", default="HEAD", help="branch to review; lets you review one without checking it out"
    )
    parser.add_argument(
        "--repo-root", default=os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    )
    args = parser.parse_args()

    files, description = collect(args.repo_root, args.pr, args.base, args.head)
    if not files:
        print("review-scope: nothing to review - {0}.".format(description))
        print("(A branch already merged into the base shows no diff. Check --base.)")
        return 0

    by_area = {}
    unmapped = []
    for path in files:
        key = area_for(path)
        if key is None:
            unmapped.append(path)
        else:
            by_area.setdefault(key, []).append(path)

    print("Reviewing {0} - {1} file(s)\n".format(description, len(files)))

    lookup = dict((key, entry) for entry in AREAS for key in [entry[0]])
    present = [key for key in REVIEW_ORDER if key in by_area]

    for key in present:
        _, label, _, rules, checker, focus = lookup[key]
        paths = by_area[key]
        print("=== {0} ({1} file(s)) ===".format(label, len(paths)))
        for path in paths[:6]:
            print("    {0}".format(path))
        if len(paths) > 6:
            print("    ... and {0} more".format(len(paths) - 6))
        if rules:
            print("  rules  {0}".format(", ".join(rules)))
        if checker:
            print("  check  {0}".format(checker))
        print("  read for:")
        for line in focus:
            print("    - {0}".format(line) if not line.startswith("  ") else "      {0}".format(line.strip()))
        print("")

    if unmapped:
        print("=== unclassified ({0} file(s)) ===".format(len(unmapped)))
        for path in unmapped[:6]:
            print("    {0}".format(path))
        print("  No rule covers these. Review on general grounds and say so.\n")

    risks = []
    for path in files:
        normalised = path.replace("\\", "/")
        for prefix, why, suffix in HIGH_RISK:
            if normalised.startswith(prefix) and (suffix is None or normalised.endswith(suffix)):
                risks.append((path, why))
                break
    if risks:
        print("HIGH RISK")
        for path, why in risks:
            print("  {0}".format(path))
            print("    {0}".format(why))
        print("")

    print("Suggested order: {0}".format(" -> ".join(present)))
    if any(key in by_area for key in ("db", "routes", "views", "auth", "tests", "app")):
        print("Then, from app/:  npm run lint && npm run test   (needs docker compose up -d)")
    print("")
    print("Report with templates/pr-review.md. Findings the checkers raise outside")
    print("this diff are pre-existing - report them separately or not at all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
