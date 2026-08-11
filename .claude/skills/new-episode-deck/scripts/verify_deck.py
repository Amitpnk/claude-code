#!/usr/bin/env python3
"""Check a deck under docs/slides/ for the mistakes that only show up on camera.

Catches: slide markers that drifted out of sync after an insert, unbalanced
tags, a static slide count or progress-bar width left at the old number,
image paths that do not exist, and leftover TODO stubs.

  python .claude/skills/new-episode-deck/scripts/verify_deck.py docs/slides/12-subagents.html
"""
import io
import os
import re
import sys


def check(path):
    problems = []
    notes = []
    html = io.open(path, encoding="utf-8").read()

    sections = re.findall(r'<section class="slide[^"]*"', html)
    markers = [int(m) for m in re.findall(r"<!-- SLIDE (\d+) -->", html)]
    total = len(sections)

    notes.append("{0} slides, {1} markers".format(total, len(markers)))

    if len(markers) != total:
        problems.append(
            "{0} slides but {1} '<!-- SLIDE n -->' markers".format(total, len(markers)))
    if markers and markers != list(range(1, len(markers) + 1)):
        bad = [i + 1 for i, m in enumerate(markers) if m != i + 1]
        problems.append(
            "slide markers are not sequential - first wrong at position {0}".format(bad[0]))

    for tag in ("section", "div"):
        opens = len(re.findall(r"<{0}[ >]".format(tag), html))
        closes = len(re.findall(r"</{0}>".format(tag), html))
        if opens != closes:
            problems.append("<{0}> unbalanced: {1} open, {2} close".format(tag, opens, closes))

    m = re.search(r'id="slideTotal">(\d+)<', html)
    if not m:
        problems.append("no id=\"slideTotal\" fallback found")
    elif int(m.group(1)) != total:
        problems.append(
            "static slideTotal is {0}, deck has {1} slides".format(m.group(1), total))

    m = re.search(r"\.top-bar \.fill \{[^}]*?width: ([\d.]+)%", html, re.S)
    if not m:
        problems.append("no .top-bar .fill width found")
    elif total and abs(float(m.group(1)) - 100.0 / total) > 0.06:
        problems.append(
            "progress-bar fill is {0}%, should be {1:.2f}% for {2} slides".format(
                m.group(1), 100.0 / total, total))

    base = os.path.dirname(os.path.abspath(path))
    for src in re.findall(r'<img[^>]+src="([^"]+)"', html):
        if src.startswith(("http://", "https://", "data:")):
            continue
        if not os.path.exists(os.path.join(base, src)):
            problems.append("missing image: {0}".format(src))

    for i, img in enumerate(re.findall(r"<img[^>]*>", html), start=1):
        if 'alt="' not in img:
            problems.append("image {0} has no alt text".format(i))

    if sections and 'class="slide title-slide active"' not in html:
        problems.append("first slide is not 'slide title-slide active'")
    if sections and "closing" not in sections[-1]:
        problems.append("last slide is not the closing slide")

    todos = html.count("TODO")
    if todos:
        problems.append("{0} TODO placeholder(s) still in the deck".format(todos))

    return problems, notes


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: verify_deck.py <deck.html> [deck.html ...]")

    failed = False
    for path in sys.argv[1:]:
        if not os.path.exists(path):
            print("{0}: FAIL - file not found".format(path))
            failed = True
            continue
        problems, notes = check(path)
        label = os.path.basename(path)
        if problems:
            failed = True
            print("{0}: FAIL ({1})".format(label, "; ".join(notes)))
            for prob in problems:
                print("  - {0}".format(prob))
        else:
            print("{0}: OK ({1})".format(label, "; ".join(notes)))

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
