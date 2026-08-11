#!/usr/bin/env python3
"""Scaffold a new episode slide deck from templates/deck.html.

Writes docs/slides/NN-slug.html with the house chrome already correct:
title slide, agenda, N empty content slides, and the closing "next video"
slide. The content slides are left as TODO stubs for Claude to fill in
using resources/slide-patterns.md.

Example:
  python .claude/skills/new-episode-deck/scripts/new_deck.py \
    --num 12 --slug subagents \
    --title "SubAgents" --subtitle "Delegate Work and Kill Token Costs" \
    --tagline "One context per job." \
    --agenda "Why one context breaks" "The orchestrator pattern" \
             "Writing an agent file" "Live demo" \
    --next-title "MCP Explained" --next-tagline "Connect Claude to your tools." \
    --content-slides 8
"""
import argparse
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
TEMPLATE = os.path.join(SKILL_DIR, "templates", "deck.html")

CONTENT_SLIDE = """  <!-- SLIDE {n} -->
  <section class="slide">
    <h2>TODO: slide {n} heading</h2>
    <div class="subtitle">TODO: one-line setup, or &amp;nbsp; if none.</div>
    <!-- TODO: pick a component from resources/slide-patterns.md -->
  </section>
"""


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--num", required=True, help="Episode number, e.g. 12")
    p.add_argument("--slug", required=True, help="Kebab-case slug, e.g. subagents")
    p.add_argument("--title", required=True, help="Episode title (before the em dash)")
    p.add_argument("--subtitle", required=True, help="Second line of the title slide")
    p.add_argument("--tagline", default="", help="Tagline under the title")
    p.add_argument("--agenda", nargs=4, required=True, metavar="ITEM",
                   help="Exactly four agenda items")
    p.add_argument("--next-title", required=True, help="Title of the next episode")
    p.add_argument("--next-tagline", default="", help="Tagline for the next episode")
    p.add_argument("--content-slides", type=int, default=8,
                   help="Number of TODO content slides between agenda and closing")
    p.add_argument("--repo-root", default=os.path.abspath(os.path.join(SKILL_DIR, "..", "..", "..")),
                   help="Repo root (defaults to three levels above the skill)")
    p.add_argument("--force", action="store_true", help="Overwrite an existing deck")
    args = p.parse_args()

    if args.content_slides < 1:
        p.error("--content-slides must be at least 1")

    num = args.num.zfill(2)
    total = 2 + args.content_slides + 1  # title + agenda + content + closing

    out_path = os.path.join(args.repo_root, "docs", "slides",
                            "{0}-{1}.html".format(num, args.slug))
    if os.path.exists(out_path) and not args.force:
        sys.exit("refusing to overwrite {0} (pass --force)".format(out_path))
    if not os.path.isdir(os.path.dirname(out_path)):
        sys.exit("no such directory: {0}".format(os.path.dirname(out_path)))

    html = io.open(TEMPLATE, encoding="utf-8").read()

    content = "\n".join(
        CONTENT_SLIDE.format(n=i) for i in range(3, 3 + args.content_slides)
    )

    subs = {
        "{{NUM}}": num,
        "{{TITLE}}": args.title,
        "{{SUBTITLE}}": args.subtitle,
        "{{TAGLINE}}": args.tagline,
        "{{TOTAL}}": str(total),
        "{{FILL}}": "{0:.2f}".format(100.0 / total),
        "{{CONTENT_SLIDES}}": content,
        "{{NEXT_TITLE}}": args.next_title,
        "{{NEXT_TAGLINE}}": args.next_tagline,
    }
    for i, item in enumerate(args.agenda, start=1):
        subs["{{{{AGENDA_{0}}}}}".format(i)] = item

    for key, value in subs.items():
        html = html.replace(key, value)

    leftover = [t for t in ("{{", "}}") if t in html]
    if leftover:
        sys.exit("template still has unsubstituted placeholders — check new_deck.py")

    io.open(out_path, "w", encoding="utf-8", newline="\n").write(html)
    print("wrote {0}".format(out_path))
    print("{0} slides: 1 title, 1 agenda, {1} TODO content, 1 closing".format(
        total, args.content_slides))
    print("next: fill the TODO slides, then run verify_deck.py")


if __name__ == "__main__":
    main()
