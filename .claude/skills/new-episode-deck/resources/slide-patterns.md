# Slide patterns

Every deck in `docs/slides/` shares one CSS block. There is no build step and no
stylesheet import — the CSS is inlined in each file, and `templates/deck.html` already
contains it. **Never invent new class names or add a `<style>` rule to a deck.** If a
slide needs something the classes below cannot express, the slide is trying to do too
much; split it.

Each pattern below is copy-paste ready. Replace the text, keep the structure.

## Slide frame

Every content slide is a `<section>` preceded by a numbered comment. The number must match
the slide's position in the file — `verify_deck.py` fails the deck if it drifts.

```html
  <!-- SLIDE 4 -->
  <section class="slide">
    <h2>Heading — short, declarative</h2>
    <div class="subtitle">One line of setup, or &nbsp; when the heading stands alone.</div>
    <!-- one component from below -->
  </section>
```

Only the first slide carries `active`; only the last carries `closing`.

## Picking a component

| Use | When | Cap |
|---|---|---|
| `num-grid` | 2–4 parallel items of equal weight, agenda, examples | 4 (`cols-1` for a single column list) |
| `check-list` | 3 points that each need a sentence of explanation | 4 |
| `split-two` | Right way vs wrong way — auto ✓ / ✗ bullets | 2 cols |
| `compare-two` | Two neutral alternatives, neither is "wrong" | 2 cols |
| `flow` | An ordered pipeline where order is the point | 5 steps |
| `code-block` | A file, a command, a transcript | 1 per slide |
| `lead-statement` | One idea that deserves a whole slide | — |
| `figure` | A screenshot | 1 per slide |
| `takeaway-list` | Closing recap, or a list of failures/wins | 5 |

Two heavy components on one slide will overflow the fixed-height stage. One per slide.

## num-grid

```html
    <div class="num-grid">
      <div class="num-card"><span class="n">01</span><div><div class="t">Card title</div><div class="d">Optional supporting line.</div></div></div>
      <div class="num-card"><span class="n">02</span><div><div class="t">Card title</div></div></div>
    </div>
```

Add `cols-1` (`<div class="num-grid cols-1">`) for a full-width stacked list. The `n` span
is not required to be a number — decks use `/` for slash commands.

## check-list

```html
    <div class="check-list">
      <div class="check-item"><span class="icon">&#10003;</span><div><div class="t">The claim</div><div class="d">Why it is true, in one sentence.</div></div></div>
    </div>
```

## split-two — good vs bad

Bullets get their marks automatically: `.good li` prefixes ✓, `.bad li` prefixes ✗. Do not
type the symbols.

```html
    <div class="split-two">
      <div class="split-col good">
        <h4>Do this</h4>
        <ul><li>Point</li><li>Point</li></ul>
      </div>
      <div class="split-col bad">
        <h4>Not this</h4>
        <ul><li>Point</li><li>Point</li></ul>
      </div>
    </div>
```

## compare-two — two valid options

Bullets are prefixed with an em dash, not a verdict mark. `teal-border` highlights the one
being recommended; omit it on both when neither wins.

```html
    <div class="compare-two">
      <div class="compare-col teal-border">
        <h4>Project-scoped</h4>
        <div class="sub">.claude/skills/</div>
        <ul><li>Point</li><li>Point</li></ul>
      </div>
      <div class="compare-col">
        <h4>User-scoped</h4>
        <div class="sub">~/.claude/skills/</div>
        <ul><li>Point</li></ul>
      </div>
    </div>
```

## flow — ordered steps

```html
    <div class="flow">
      <div class="flow-step"><div class="t">Identify</div><div class="d">the need</div></div>
      <div class="flow-arrow">&rarr;</div>
      <div class="flow-step"><div class="t">Write</div><div class="d">SKILL.md</div></div>
    </div>
```

The `d` line renders in mono at 11px — keep it to two or three words. On narrow screens the
row stacks and the arrows rotate automatically.

## code-block

```html
    <div class="code-block">
      <div class="code-title">.claude/skills/my-skill/SKILL.md</div>
      <pre><span class="c-h">---</span>
name: my-skill
<span class="c-dim"># dimmed comment</span></pre>
    </div>
```

Spans: `c-h` teal heading, `c-prompt` muted prompt, `c-ok` teal success, `c-you` white user
input, `c-dim` faint. Escape `<` and `>` as `&lt;` `&gt;` inside `<pre>`. Keep it under
about 14 lines — the block does not scroll.

## lead-statement

```html
    <div class="lead-statement">A skill is <span class="hl">expertise on demand</span>, not another prompt you retype.</div>
```

## figure — screenshots

Images live in `docs/slides/img/`. Reference them relatively. Alt text is required and
`verify_deck.py` enforces it — describe what the image shows, not "screenshot".

```html
    <div class="figure">
      <img src="img/skills-folderstructure.png" alt="A folder labelled CLAUDE SKILL containing SKILL.md, scripts/, templates/ and resources.">
    </div>
    <div class="fig-note"><span class="k">note</span>What to look at in the image.</div>
```

`max-height: 48vh` keeps a tall screenshot inside the stage. A wide screenshot with small
text will be unreadable on video — crop it before adding it.

## takeaway-list

```html
    <div class="takeaway-list">
      <div class="takeaway-item neg"><span class="mark">&#10007;</span><p>What goes wrong.</p></div>
      <div class="takeaway-item pos"><span class="mark">&#10003;</span><p>What to do instead.</p></div>
    </div>
```

## Closing slide

The last slide is always `class="slide closing"` and always points at the next episode —
that is the series convention, and the deck reads as unfinished without it. Episode 15
points back at the playlist instead. `templates/deck.html` already contains it.

## Writing for video

- Headings are read aloud. Write them as sentences a person would say.
- No paragraphs. If a point needs more than about 20 words, it is two slides.
- Use `&nbsp;` for an empty `.subtitle` rather than deleting the div — the spacing depends
  on it.
- Real paths and real commands only. This series is watched with the repo open.
