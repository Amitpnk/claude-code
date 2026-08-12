#!/usr/bin/env python3
"""Check a commit message against this repo's convention before it is committed.

Catches the failures this repo's history actually contains: gerund subjects
("adding seed skills"), placeholder subjects ("Update settings.json"), a missing
blank line before the body, and unwrapped body text.

Heuristic: it reads the message as text. It cannot tell whether the type is the
right one or whether the body is true.

  python .claude/skills/commit-message/scripts/check_message.py -m "$(cat msg.txt)"
  python .claude/skills/commit-message/scripts/check_message.py .git/COMMIT_EDITMSG
  git log -1 --format=%B | python .claude/skills/commit-message/scripts/check_message.py -
"""
import argparse
import io
import re
import sys

TYPES = [
    "feat",
    "fix",
    "docs",
    "refactor",
    "test",
    "chore",
    "perf",
    "build",
    "ci",
    "style",
    "revert",
]

# Kept in sync with the scope table in SKILL.md - adding one here without adding
# it there gives you a checker that accepts a scope nobody documented.
SCOPES = [
    "app",
    "db",
    "routes",
    "views",
    "tests",
    "auth",
    "docs",
    "slides",
    "scripts",
    "claude",
    "skills",
    "rules",
    "commands",
    "specs",
    "plans",
    "deps",
]

SUBJECT_MAX = 72
SUBJECT_IDEAL = 50
BODY_MAX = 72

HEADER_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!?): (?P<desc>.+)$")
TRAILER_RE = re.compile(r"^[A-Z][A-Za-z-]+: .+$")
URL_RE = re.compile(r"https?://\S{20,}")

# Past-tense openers that are not also valid imperatives ("update" and "fix" are).
PAST_TENSE = [
    "added",
    "changed",
    "created",
    "deleted",
    "fixed",
    "made",
    "moved",
    "removed",
    "renamed",
    "updated",
    "wrote",
]

# Third person: "adds a field", "fixes the drift".
THIRD_PERSON_RE = re.compile(
    r"^(add|update|remove|create|delete|move|rename|change|drop|bump|allow|"
    r"reject|return|throw|render)s$|^(fix|match|pass|dispatch)es$"
)

PLACEHOLDER_RE = re.compile(
    r"^(wip|misc|stuff|cleanup|changes|various|minor (changes|fixes|edits)|"
    r"update(s)?|fix(es)?|edit(s)?|tweak(s)?|final|done|asdf|temp|test commit)$"
)

# "Update 11-claude-code-skills.html" - a filename is not a description.
FILENAME_ONLY_RE = re.compile(r"^\S+\.(html|md|ts|js|json|css|py|yml|yaml|sql)$")


def read_message(args):
    if args.message is not None:
        return args.message
    if args.path in (None, "-"):
        return sys.stdin.read()
    return io.open(args.path, encoding="utf-8").read()


def strip_comments(text):
    """Drop the lines git itself would drop, and any trailing blank lines."""
    lines = [line for line in text.replace("\r\n", "\n").split("\n") if not line.startswith("#")]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def check_mood(first, findings):
    lowered = first.lower().strip(",")
    if lowered.endswith("ing") and lowered not in ("bring", "string", "ping"):
        findings.append(
            (
                "subject/mood",
                "Subject starts with a gerund "
                + repr(first)
                + '. Use the imperative - "add", not "adding". The subject completes '
                + '"this commit will ...".',
            )
        )
    elif lowered in PAST_TENSE:
        findings.append(
            ("subject/mood", "Subject is past tense " + repr(first) + ". Use the imperative.")
        )
    elif THIRD_PERSON_RE.match(lowered):
        findings.append(
            ("subject/mood", "Subject is third person " + repr(first) + ". Use the imperative.")
        )


def check_scope(scope, findings):
    if not scope.strip():
        findings.append(("subject/scope", "Empty scope - omit the parentheses instead."))
        return
    for part in [s.strip() for s in scope.split(",")]:
        if part not in SCOPES:
            findings.append(
                (
                    "subject/scope",
                    "Unknown scope "
                    + repr(part)
                    + ". Known: "
                    + ", ".join(SCOPES)
                    + ". Add it to both scripts if it is genuinely new.",
                )
            )


def check_subject(subject, findings):
    if not subject.strip():
        findings.append(("subject/empty", "The message is empty."))
        return None

    match = HEADER_RE.match(subject)
    if not match:
        findings.append(
            (
                "subject/format",
                "Subject is not '<type>(<scope>): <description>'. Got: " + repr(subject),
            )
        )
        stripped = subject.strip()
        words = stripped.split()
        names_a_file = len(words) <= 3 and any(FILENAME_ONLY_RE.match(word) for word in words)
        if PLACEHOLDER_RE.match(stripped.lower()) or names_a_file:
            findings.append(
                (
                    "subject/placeholder",
                    "It also names a file or says nothing - describe the change, not the path.",
                )
            )
        return None

    ctype = match.group("type")
    scope = match.group("scope")
    desc = match.group("desc")

    if ctype not in TYPES:
        findings.append(
            ("subject/type", "Unknown type " + repr(ctype) + ". Use one of: " + ", ".join(TYPES))
        )

    if scope is not None:
        check_scope(scope, findings)

    if len(subject) > SUBJECT_MAX:
        findings.append(
            (
                "subject/length",
                "Subject is {0} chars, limit is {1}. Move the detail into the body.".format(
                    len(subject), SUBJECT_MAX
                ),
            )
        )

    if desc.endswith("."):
        findings.append(("subject/period", "Subject ends with a period. Drop it."))

    words = desc.split()
    first = words[0] if words else ""

    if first[:1].isupper() and not first.isupper():
        findings.append(
            ("subject/case", "Description starts with a capital: " + repr(first) + ". Lowercase it.")
        )

    check_mood(first, findings)

    stripped_desc = desc.strip()
    if PLACEHOLDER_RE.match(stripped_desc.lower()):
        findings.append(
            (
                "subject/placeholder",
                "Description " + repr(desc) + " says nothing. Name what changed and why.",
            )
        )
    elif FILENAME_ONLY_RE.match(stripped_desc):
        findings.append(
            (
                "subject/placeholder",
                "Description is a filename. The diff already lists files - say what changed.",
            )
        )

    return len(subject)


def check_body(lines, findings, notes):
    if len(lines) < 2:
        notes.append("no body - acceptable only if the subject genuinely says everything")
        return

    if lines[1].strip():
        findings.append(
            ("body/blank-line", "Line 2 must be blank - git treats the first line as the subject.")
        )

    # From line 2, not line 3: when the blank line is missing the body shifts up,
    # and an unwrapped line there should still be reported.
    in_fence = False
    for index, line in enumerate(lines[1:], start=2):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or TRAILER_RE.match(line) or URL_RE.search(line):
            continue
        if len(line) > BODY_MAX:
            findings.append(
                (
                    "body/wrap",
                    "Line {0} is {1} chars; wrap the body at {2}.".format(
                        index, len(line), BODY_MAX
                    ),
                )
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="message file, or - for stdin (the default)")
    parser.add_argument("-m", "--message", help="the message itself")
    args = parser.parse_args()

    lines = strip_comments(read_message(args))
    findings, notes = [], []

    length = check_subject(lines[0] if lines else "", findings)
    check_body(lines, findings, notes)

    if length is not None and length <= SUBJECT_MAX:
        if length > SUBJECT_IDEAL:
            notes.append(
                "subject is {0} chars - under the {1} limit, but {2} reads better in "
                "'git log --oneline'".format(length, SUBJECT_MAX, SUBJECT_IDEAL)
            )
        else:
            notes.append("subject is {0} chars".format(length))

    for note in notes:
        print("  ok  {0}".format(note))
    print("")

    if not findings:
        print("check-message: OK - well-formed. Whether it is accurate is still yours to judge.")
        return 0

    by_rule = {}
    for rule, message in findings:
        by_rule.setdefault(rule, []).append(message)

    print("check-message: {0} finding(s)\n".format(len(findings)))
    for rule in sorted(by_rule):
        print("[{0}]".format(rule))
        for message in by_rule[rule]:
            print("  {0}".format(message))
        print("")
    return 1


if __name__ == "__main__":
    sys.exit(main())
