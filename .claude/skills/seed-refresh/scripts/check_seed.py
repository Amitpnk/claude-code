#!/usr/bin/env python3
"""Check that app/src/db/seed.ts exercises the shapes the app can actually render.

A seed is sample data, but it is also the only thing most people ever look at
while developing. Anything it never produces is a view branch nobody sees.

Heuristic: reads schema.ts, seed.ts and styles.css as text. Check every finding
at the line it cites before acting on it.

  python .claude/skills/seed-refresh/scripts/check_seed.py
"""
import argparse
import io
import os
import re
import sys

ENUM_RE = re.compile(r"export const (\w+)\s*=\s*pgEnum\(\s*[\"'](\w+)[\"']\s*,\s*\[([^\]]*)\]")
# A column declaration may span several lines, e.g.
#   projectId: integer("project_id")
#     .notNull()
#     .references(() => projects.id, { onDelete: "cascade" }),
# so columns are split on top-level commas rather than matched line by line.
COLUMN_RE = re.compile(r"^\s*(\w+)\s*:\s*(\w+)\(", re.S)
TABLE_RE = re.compile(r"export const (\w+)\s*=\s*pgTable\(\s*[\"'](\w+)[\"']\s*,\s*\{", re.S)
DESTRUCTURE_RE = re.compile(r"const\s*\[([^\]]+)\]\s*=\s*await\s+db\s*\n?\s*\.insert\(projects\)")


def read(path):
    return io.open(path, encoding="utf-8").read()


def line_at(text, offset):
    return text.count("\n", 0, offset) + 1


def parse_enums(schema):
    """{ ts_name: (pg_name, [values...], line) }"""
    enums = {}
    for match in ENUM_RE.finditer(schema):
        values = re.findall(r"[\"'](\w+)[\"']", match.group(3))
        enums[match.group(1)] = (match.group(2), values, line_at(schema, match.start()))
    return enums


def split_top_level(body):
    """Split an object literal body on commas that are not nested."""
    chunks, depth, start = [], 0, 0
    for i, char in enumerate(body):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            chunks.append((start, body[start:i]))
            start = i + 1
    if body[start:].strip():
        chunks.append((start, body[start:]))
    return chunks


def matching_brace(text, open_index):
    depth = 0
    for i in range(open_index, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text)


def parse_tables(schema):
    """{ ts_name: {"columns": {field: {"optional": bool, "line": int}}} }"""
    tables = {}
    for match in TABLE_RE.finditer(schema):
        name, start = match.group(1), match.start()
        open_index = schema.rindex("{", 0, match.end())
        body_start = open_index + 1
        body = schema[body_start : matching_brace(schema, open_index)]

        columns = {}
        for offset, chunk in split_top_level(body):
            head = COLUMN_RE.match(chunk)
            if not head:
                continue
            field, kind = head.group(1), head.group(2)
            if kind == "serial" or ".primaryKey()" in chunk:
                continue
            # A foreign key is structurally required even when .notNull() is absent.
            optional = ".notNull()" not in chunk and ".references(" not in chunk
            columns[field] = {
                "optional": optional,
                "line": line_at(schema, body_start + offset),
                "kind": kind,
            }
        tables[name] = {"columns": columns, "line": line_at(schema, start)}
    return tables


def values_blocks(seed):
    """[(table, [row_text, ...], line)] for each db.insert(<table>).values([...])"""
    blocks = []
    for match in re.finditer(r"\.insert\((\w+)\)[\s\S]{0,80}?\.values\(", seed):
        table = match.group(1)
        i = seed.index("(", match.end() - 1)
        depth, j = 0, i
        while j < len(seed):
            if seed[j] in "([{":
                depth += 1
            elif seed[j] in ")]}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        body = seed[i + 1 : j]
        rows = []
        depth, start = 0, None
        for k, char in enumerate(body):
            if char == "{":
                if depth == 0:
                    start = k
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    rows.append(body[start : k + 1])
                    start = None
        blocks.append((table, rows, line_at(seed, match.start())))
    return blocks


def audit(root):
    findings = []
    notes = []
    db_dir = os.path.join(root, "app", "src", "db")
    schema_path = os.path.join(db_dir, "schema.ts")
    seed_path = os.path.join(db_dir, "seed.ts")
    css_path = os.path.join(root, "app", "src", "public", "styles.css")

    if not os.path.exists(seed_path):
        sys.exit("not a TaskFlow checkout: {0} not found".format(seed_path))

    schema = read(schema_path)
    seed = read(seed_path)
    css = read(css_path) if os.path.exists(css_path) else ""

    enums = parse_enums(schema)
    tables = parse_tables(schema)
    blocks = values_blocks(seed)

    def add(where, rule, message):
        findings.append((where, rule, message))

    # 1. every enum value appears somewhere in the seed
    seeded_literals = set(re.findall(r"[\"'](\w+)[\"']", seed))
    for ts_name, (pg_name, values, line) in sorted(enums.items()):
        missing = [v for v in values if v not in seeded_literals]
        if missing:
            add(
                "app/src/db/schema.ts:{0}".format(line),
                "seed/enum-coverage",
                "{0} value(s) {1} never appear in the seed - the badge and ordering paths for "
                "them are never rendered".format(pg_name, ", ".join(missing)),
            )
        else:
            notes.append("{0}: all {1} value(s) seeded".format(pg_name, len(values)))

    # 2. optional columns are never absent
    for table, rows, line in blocks:
        columns = tables.get(table, {}).get("columns", {})
        if not rows:
            continue
        for field, meta in sorted(columns.items()):
            if not meta["optional"]:
                continue
            present = sum(1 for row in rows if re.search(r"\b{0}\s*:".format(field), row))
            if present == len(rows):
                add(
                    "app/src/db/seed.ts:{0}".format(line),
                    "seed/optional-columns",
                    "{0}.{1} is nullable but every seeded row sets it - the empty case is "
                    "never rendered".format(table, field),
                )

    # 3. parent rows with zero and with exactly one child.
    #
    # A project with no tasks is never referenced in the tasks insert, so it
    # cannot be a *used* destructured variable without tripping no-unused-vars.
    # Counting the rows in the projects values block instead of only the
    # destructured names lets a zero-task project be seeded without one.
    match = DESTRUCTURE_RE.search(seed)
    total_projects = 0
    for table, rows, _line in blocks:
        if table == "projects":
            total_projects = len(rows)
    if match and total_projects:
        parents = [n.strip() for n in match.group(1).split(",") if n.strip()]
        counts = {}
        for parent in parents:
            counts[parent] = len(re.findall(r"projectId:\s*{0}\.id".format(parent), seed))
        named_with_tasks = sum(1 for c in counts.values() if c > 0)
        childless = total_projects - named_with_tasks
        line = line_at(seed, match.start())

        if childless <= 0:
            add(
                "app/src/db/seed.ts:{0}".format(line),
                "seed/collection-shapes",
                "every seeded project has tasks - the empty task list is never rendered",
            )
        if not any(c == 1 for c in counts.values()):
            add(
                "app/src/db/seed.ts:{0}".format(line),
                "seed/collection-shapes",
                "no seeded project has exactly one task - the singular label is never "
                "rendered",
            )
        notes.append(
            "{0} project(s) seeded; tasks per named project: {1}; with no tasks: {2}".format(
                total_projects,
                ", ".join("{0}={1}".format(p, counts[p]) for p in parents),
                childless,
            )
        )

    # 4. every enum value has a badge style
    if css:
        for ts_name, (pg_name, values, _line) in sorted(enums.items()):
            field = pg_name.split("_", 1)[1] if "_" in pg_name else pg_name
            prefix = "task" if field == "status" else field
            for value in values:
                selector = ".{0}-badge--{1}".format(prefix, value)
                if selector not in css:
                    add(
                        "app/src/public/styles.css",
                        "seed/badge-styles",
                        "{0} has no rule - a seeded row with {1}={2} renders an unstyled "
                        "badge".format(selector, field, value),
                    )

    return findings, notes


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument(
        "--repo-root", default=os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    )
    args = parser.parse_args()

    findings, notes = audit(args.repo_root)

    for note in notes:
        print("  ok  {0}".format(note))
    print("")

    if not findings:
        print("check-seed: OK - the seed covers every shape checked")
        return 0

    by_rule = {}
    for where, rule, message in findings:
        by_rule.setdefault(rule, []).append((where, message))

    print("check-seed: {0} gap(s)\n".format(len(findings)))
    for rule in sorted(by_rule):
        print("[{0}]".format(rule))
        for where, message in by_rule[rule]:
            print("  {0}".format(message))
            print("    -> {0}".format(where))
        print("")
    return 1


if __name__ == "__main__":
    sys.exit(main())
