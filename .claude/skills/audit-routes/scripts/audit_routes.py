#!/usr/bin/env python3
"""Audit the two TaskFlow route surfaces for drift and contract violations.

Heuristic, not a type checker: it reads app/src/app.ts and
app/src/routes/*.routes.ts as text and reports the specific mistakes this
codebase keeps making. Every finding cites a file and line so a human can
check it. Read the cited line before acting on a finding.

  python .claude/skills/audit-routes/scripts/audit_routes.py
"""
import argparse
import io
import os
import re
import sys

ROUTE_RE = re.compile(
    r"^(?P<indent>\s*)(?P<obj>app|\w*[Rr]outer)\.(?P<verb>get|post|put|patch|delete)"
    r"\(\s*[\"'](?P<path>[^\"']+)[\"']",
    re.M,
)

# HTML routes that are the same resource operation as an /api route but cannot
# be derived by rewriting the path.
ALIASES = {
    ("get", "/"): ("get", "/projects"),
}

PAGE_PATHS = {"/about", "/terms", "/privacy", "/login", "/logout"}

MUTATING = ("post", "put", "patch", "delete")


class Handler(object):
    def __init__(self, verb, path, filename, line, body):
        self.verb = verb
        self.path = path
        self.file = filename
        self.line = line
        self.body = body

    @property
    def where(self):
        return "{0}:{1}".format(self.file, self.line)

    @property
    def label(self):
        return "{0} {1}".format(self.verb.upper(), self.path)

    def canonical(self):
        """Reduce a route to the resource operation it performs."""
        verb, path = self.verb, self.path
        if path.startswith("/api"):
            path = path[4:] or "/"
        # Browser forms cannot issue DELETE, so POST .../delete is a delete.
        if verb == "post" and path.endswith("/delete"):
            verb, path = "delete", path[: -len("/delete")]
        path = re.sub(r":\w+", ":x", path)
        return ALIASES.get((verb, path), (verb, path))


def read(path):
    return io.open(path, encoding="utf-8").read()


def extract(text, filename):
    """Split a file into handlers. A handler runs until the next route decl."""
    matches = list(ROUTE_RE.finditer(text))
    out = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        line = text.count("\n", 0, start) + 1
        out.append(
            Handler(match.group("verb"), match.group("path"), filename, line, text[start:end])
        )
    return out


def line_of(handler, offset):
    return handler.line + handler.body.count("\n", 0, offset)


def is_resource_route(handler):
    if handler.path in PAGE_PATHS:
        return False
    return handler.path == "/" or "project" in handler.path


def audit(root):
    findings = []
    app_path = os.path.join(root, "app", "src", "app.ts")
    routes_dir = os.path.join(root, "app", "src", "routes")

    if not os.path.exists(app_path):
        sys.exit("not a TaskFlow checkout: {0} not found".format(app_path))

    sources = {"app/src/app.ts": read(app_path)}
    for name in sorted(os.listdir(routes_dir)):
        if name.endswith(".routes.ts"):
            sources["app/src/routes/" + name] = read(os.path.join(routes_dir, name))

    everything = []
    for filename, text in sorted(sources.items()):
        everything.extend(extract(text, filename))

    # The surface a route belongs to is decided by its path, not by which file it
    # lives in. auth.routes.ts is a router that serves the HTML surface.
    api = [h for h in everything if h.path.startswith("/api")]
    html = [h for h in everything if not h.path.startswith("/api")]
    json_files = {h.file for h in api}

    def add(where, rule, message):
        findings.append((where, rule, message))

    for handler in everything:
        if handler.file in json_files and not handler.path.startswith("/api"):
            add(
                handler.where,
                "api-style/paths",
                "{0} sits on a JSON router but outside /api - the error middleware keys off "
                "req.path.startsWith('/api'), so failures render HTML".format(handler.label),
            )

        for match in re.finditer(r"res\.status\((\d{3})\)\s*\.\s*(json|render|send)", handler.body):
            code = int(match.group(1))
            if code >= 400:
                add(
                    "{0}:{1}".format(handler.file, line_of(handler, match.start())),
                    "architecture/error-handling",
                    "{0} formats a {1} inline - throw an AppError so the single error "
                    "middleware formats it".format(handler.label, code),
                )

        first_line = handler.body.split("\n")[0]
        if "async" in first_line and "try {" not in handler.body:
            add(
                handler.where,
                "architecture/error-handling",
                "{0} is async with no try/catch - a rejection escapes Express 4 instead of "
                "reaching the error middleware".format(handler.label),
            )

        for match in re.finditer(r"Number\(req\.params\.(\w+)\)", handler.body):
            add(
                "{0}:{1}".format(handler.file, line_of(handler, match.start())),
                "validation/ids",
                "{0} parses :{1} with Number() and never checks NaN - a non-numeric id "
                "reaches the database as NaN".format(handler.label, match.group(1)),
            )

        if (
            not handler.path.startswith("/api")
            and handler.verb in MUTATING
            and is_resource_route(handler)
            and "requireAuth" not in handler.body
        ):
            add(
                handler.where,
                "auth/guards",
                "{0} mutates without requireAuth - every other mutating HTML route is "
                "guarded".format(handler.label),
            )

    html_ops = {}
    for handler in html:
        if is_resource_route(handler):
            html_ops.setdefault(handler.canonical(), handler)
    api_ops = {}
    for handler in api:
        api_ops.setdefault(handler.canonical(), handler)

    for op in sorted(set(api_ops) - set(html_ops)):
        handler = api_ops[op]
        add(
            handler.where,
            "architecture/dual-surface",
            "{0} has no HTML equivalent - confirm that is deliberate".format(handler.label),
        )
    for op in sorted(set(html_ops) - set(api_ops)):
        handler = html_ops[op]
        add(
            handler.where,
            "architecture/dual-surface",
            "{0} has no /api equivalent - confirm that is deliberate".format(handler.label),
        )

    for op in sorted(set(html_ops) & set(api_ops)):
        page, json_route = html_ops[op], api_ops[op]
        # An inline 404 is a real existence check, just formatted the wrong way.
        # That is already reported under architecture/error-handling.
        handles_missing = re.search(r"res\.status\(4\d\d\)", page.body) is not None
        for symbol, what in (
            ("ValidationError", "input validation"),
            ("NotFoundError", "an existence check"),
        ):
            if symbol == "NotFoundError" and handles_missing:
                continue
            if symbol in json_route.body and symbol not in page.body:
                add(
                    page.where,
                    "architecture/dual-surface",
                    "{0} skips {1} that its twin {2} performs".format(
                        page.label, what, json_route.label
                    ),
                )

    for helper in ("byPriorityThenCreatedAt",):
        homes = [f for f, s in sources.items() if re.search(r"const {0}\s*=".format(helper), s)]
        if len(homes) > 1:
            add(
                homes[0],
                "architecture/shared-code",
                "{0} is defined in {1} files ({2}) - move it to src/lib/ so task ordering "
                "changes in one place".format(helper, len(homes), ", ".join(homes)),
            )

    return findings


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    here = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument(
        "--repo-root", default=os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    )
    args = parser.parse_args()

    findings = audit(args.repo_root)
    if not findings:
        print("audit-routes: OK - no contract violations found")
        return 0

    by_rule = {}
    for where, rule, message in findings:
        by_rule.setdefault(rule, []).append((where, message))

    print("audit-routes: {0} finding(s)\n".format(len(findings)))
    for rule in sorted(by_rule):
        print("[{0}]".format(rule))
        for where, message in by_rule[rule]:
            print("  {0}".format(message))
            print("    -> {0}".format(where))
        print("")
    return 1


if __name__ == "__main__":
    sys.exit(main())
