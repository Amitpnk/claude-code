# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Source for the GitHub Pages site (`docs/`) for "Learn Claude Code the Right Way", a 15-video
series on structured, disciplined AI-assisted development with Claude Code, plus TaskFlow
(`app/`), the companion demo app used on-camera throughout the series.

Live site: https://amitpnk.github.io/claude-code-mastery/

## Repo layout

This repo has two independent parts — there is no shared build or dependency graph between them —
plus the Claude Code configuration that applies to both:

- **`docs/`** — the static GitHub Pages site itself: `docs/index.html` is the landing page listing
  all episodes (each entry has `status`, `youtube`, `article`, `slides` fields), and
  `docs/slides/NN-episode-slug.html` are the standalone per-episode slide decks. Plain HTML/CSS,
  no build step.
- **`app/`** — TaskFlow, the real Node.js/TypeScript/Express/Postgres demo app used to illustrate
  CLAUDE.md, Skills, SubAgents, Spec-Driven Development, Plan Mode, MCP, and Hooks across the
  series. Has its own dependencies, tests, and conventions — see **[app/CLAUDE.md](app/CLAUDE.md)**
  before making any change under `app/`.
- **`.claude/`** — the Claude Code configuration this repo ships with: shared permissions,
  the `/create-spec` command, the `add-task-field` skill, topic rules, and feature specs.
  See **[.claude/README.md](.claude/README.md)** for what each subfolder is and when it loads.

When a task touches `app/`, treat `app/CLAUDE.md` as the authoritative guide for commands and
architecture; this file only covers the repo as a whole.

## Adding materials for a new episode

1. Build the slide deck as `docs/slides/NN-episode-slug.html`, matching the episode number/title in
   the `videos` array in `docs/index.html`. Follow the structure of an existing deck (same CSS
   classes, 11-slide shape ending in a "next video" closing slide) for visual consistency across
   the series.
2. Write the voiceover script as `docs/scripts/NN-episode-slug.md`, mirroring the deck slide-by-slide
   with timestamps.
3. In `docs/index.html`, update that episode's entry: set `status: "live"`, and point `youtube`,
   `article`, and `slides` at the real URLs (`slides` can link to `docs/slides/NN-episode-slug.html`
   in this repo).
