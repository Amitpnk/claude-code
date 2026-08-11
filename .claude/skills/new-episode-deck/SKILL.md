---
name: new-episode-deck
description: Build or update a slide deck for an episode of the "Learn Claude Code the Right Way" series in docs/slides/. Use for requests like "create the deck for episode 12", "add slides on X to the MCP deck", or "check deck 07". Handles the house template, the shared CSS component set, slide numbering, and the docs/index.html entry.
---

# Episode slide decks

Decks live in `docs/slides/NN-episode-slug.html`. Each is a standalone HTML file with its
CSS and navigation JS inlined — no build step, no shared stylesheet. That means every deck
carries its own copy of the design system, so consistency is maintained by *starting from
the template*, never by hand-writing a deck from scratch.

`resources/slide-patterns.md` is the catalog of available components. Read it before
writing any slide content — it is the only source for which class names exist.

## Creating a new deck

**1. Get the episode facts.** The `videos` array in `docs/index.html` is authoritative for
the number, title and description. The title splits at the em dash: the part before it is
`--title`, the part after is `--subtitle`. The *next* episode's entry gives you the closing
slide. Don't invent a title that disagrees with the index.

**2. Scaffold it.**

```bash
python .claude/skills/new-episode-deck/scripts/new_deck.py \
  --num 12 --slug subagents \
  --title "SubAgents" --subtitle "Delegate Work and Kill Token Costs" \
  --tagline "One context per job." \
  --agenda "Why one context breaks" "The orchestrator pattern" \
           "Writing an agent file" "Live demo" \
  --next-title "MCP Explained" --next-tagline "Connect Claude to your tools." \
  --content-slides 8
```

This writes the file with the title, agenda and closing slides finished, the counter and
progress bar already correct, and `--content-slides` TODO stubs in between. It refuses to
overwrite an existing deck without `--force`.

**3. Fill the content slides.** Replace each TODO stub, working from
`resources/slide-patterns.md`. One component per slide. Keep the `<!-- SLIDE n -->`
comments matching their position.

**4. Verify.**

```bash
python .claude/skills/new-episode-deck/scripts/verify_deck.py docs/slides/12-subagents.html
```

Must print `OK`. It catches the failures that are invisible until the deck is on screen:
drifted slide numbers, unbalanced tags, a stale static slide count or progress-bar width,
missing images, images without alt text, and leftover TODOs.

**5. Update `docs/index.html`.** In that episode's entry set `status: "live"` and point
`slides` at `slides/NN-episode-slug.html`. Leave `youtube` and `article` alone unless you
were given real URLs — `null` and `"https://medium.com"` are the intentional placeholders.

**6. Write the voiceover script** at `docs/scripts/NN-episode-slug.md`, mirroring the deck
slide by slide with timestamps. Create `docs/scripts/` if it does not exist yet.

## Adding slides to an existing deck

The counter, progress bar and dots are computed from `slides.length` at runtime, so they
adapt on their own — but three things do not, and all three are what break decks:

- The `<!-- SLIDE n -->` comments after the insertion point. **Renumber every one of them.**
- The static `id="slideTotal">N<` fallback in the header.
- The `.top-bar .fill { width: N% }` rule in the CSS — it should be `100 / total`.

Insert the new `<section>` at the right position, fix all three, then run
`verify_deck.py`. Do not reorder or delete existing slides unless asked; if new content
makes an existing slide redundant, say so and let the user decide.

If the deck grows well past the ~11-slide house shape, mention it — the series convention
is in the root `CLAUDE.md`, and a long deck may be better split across two episodes.

## Rules

- Never add a `<style>` block or a new class name to a deck. The inlined CSS is the
  complete design system; `resources/slide-patterns.md` lists all of it.
- Never link an external stylesheet or script. Google Fonts is the only remote resource,
  and it is already in the template.
- The first slide is always `slide title-slide active`. The last is always `slide closing`
  and points at the next episode.
- Images go in `docs/slides/img/` and are referenced relatively (`img/name.png`). Look at
  the image before writing its alt text.
- Use the real filename on disk, even when it looks like a typo — several images in
  `img/` are misspelled and renaming them would break the decks that already use them.
