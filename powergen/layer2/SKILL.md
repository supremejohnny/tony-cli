# template

Author a `template.schema.json` for a `.pptx` template so PowerGen CLI can
(a) clone branded slides with text substitution and (b) render content slides
with consistent design tokens.

## When to use

Trigger this skill whenever a new `.pptx` template is added to PowerGen, or an
existing one is being upgraded. The deliverable is always a single
`template.schema.json` co-located with the source `.pptx`.

Do NOT use this skill for: generating a presentation from content (that's the
composer's job), or for pure visual restyling without changing the schema.

---

## Why this schema exists (read before editing)

### The two-layer problem

A real `.pptx` template contains two fundamentally different kinds of slides,
and the model's job is different for each:

| Kind | Examples | What the model should do |
|---|---|---|
| **Reusable** | cover, mentor intro, section divider, "red line" grid, closing | Clone the slide verbatim, substitute text in named slots. Do not regenerate layout. |
| **Generated** | a list of N courses, a bullet summary, a custom flow diagram | Use a `content_type` → renderer mapping. Read design tokens from the schema. Generate from scratch. |

A template that tries to make the model "understand the visual style and
freestyle every slide" is unstable — the model drifts, spacing breaks, brand
identity erodes. A template that tries to make every slide reusable can't
handle variable-length content (e.g. "this student is taking 3 courses, that
one is taking 7"). The schema explicitly separates these two paths.

### Why not every slide should become a reusable (the overfitting trap)

The most dangerous failure mode when authoring a schema is to walk through
the source `.pptx` page by page and turn every page into a reusable entry.
For a 50-page template this produces 30+ reusable slides, none of which can
ever be reused outside this one template. That's not a schema, that's a
verbose copy of the original `.pptx` — and it reproduces the exact failure
of an earlier "Layer 2" approach where the model was given too many specific
patterns to choose from and couldn't generalize.

A slide should only become a `reusable` entry if it satisfies BOTH:

1. **High reuse** — used ≥2 times in this template, OR a structurally
   identical slide is expected in other templates of the same family
   (covers, section dividers, mentor profiles all qualify).
2. **High structural complexity** — the renderer (`card`, `flow`, `bullet`,
   etc.) cannot reproduce the visual to ≥90% fidelity using only the design
   tokens. If a `text_block` renderer with the right tokens would look
   essentially identical, the slide does NOT need to be a reusable.

Slides that pass (1) but not (2) → make them `generated` with the right
content_type and let the renderer handle them.

Slides that pass (2) but not (1) (i.e. a one-off complex page that only
appears in this template) → mark them `reuse_tier: "template_local"`. They
are still reusable, but only within this single template, and they do NOT
become part of the cross-template pattern library.

Slides that pass both → mark them `reuse_tier: "pattern"`. These are the
canonical reusables that get a generic name (e.g. `numbered_card_grid_v`,
not `red_line_grid_2`) and can be carried over when authoring future
templates with similar structures.

A 50-page template should typically yield **5-10 pattern reusables, plus
0-3 template_local reusables, plus the rest as generated**. If your count
is far above this, you are overfitting — go back and reclassify.

### Why slot names alone don't work

Inspecting `test.pptx` revealed:

- The cover slide has **two** shapes both named `TextBox 15` (one for student,
  one for advisor). Identifying slots by name alone produces collisions.
- The "red line" grid has two cards, each containing shapes named
  `文本占位符 9`, `文本占位符 12`, etc. Same name, different cards.
- Some shapes are positional decorations (lines, icons) that should never be
  treated as slots even though they have names.

So slot identification needs a composite key. The schema supports three
strategies, in this order of preference:

1. **`shape_name` only** — when the name is unique on the slide.
2. **`shape_name` + `nth`** — pick the Nth shape with that name (0-indexed,
   document order).
3. **`shape_name` + `near` (top/left in inches)** — pick the shape whose
   position is closest to the given coordinates. Used for grid cells where
   document order is unreliable.

Always prefer (1). Fall back to (2) when names repeat in document order. Use
(3) only when (1) and (2) both fail (e.g. designer reordered shapes).

### Why design tokens are minimal

The temptation is to extract every font, color, spacing value into tokens.
Don't. Tokens that no renderer reads are dead weight, and over-extracting from
one template makes the schema unportable to the next.

Extract **only tokens that a content renderer will actually consume**. For
PowerGen v1, that's:

- 1 primary color (titles, accents on generated slides)
- 2-4 accent colors (used in stat callouts, category headers — these are real
  in `test.pptx`: `#7578EC`, `#F7B802`, `#F18703`, `#F35B06`)
- 1 title font name + size range
- 1 body font name + size range
- 1 logo image path (extracted from the template, used as corner mark on
  generated slides)

If a future renderer needs more, add it then. Tokens grow with renderers, not
ahead of them.

### Why slots have a `kind` field

Not every slot is plain text. The schema distinguishes:

- `text` — single line, replace verbatim
- `multiline` — paragraph, may contain `\n` or vertical tab `\v` line breaks
- `repeating` — a group of slots that repeats N times (e.g. the 4 cards in the
  consequence grid). Renderer duplicates the group and fills each instance.
- `image` — replace the image binary, keep position/size
- `optional_hint` — placeholder text the user is meant to delete (e.g.
  "老师请介绍选课/换课/drop相关时间线（阅后删除）"). If the user provides
  no value, the slot is emptied rather than left as the hint.

`optional_hint` exists because `test.pptx` slide 11 literally contains an
instruction-to-the-user as placeholder text. Without this kind, a naïve
"replace if value provided, else keep template text" rule would ship that
instruction to the end user.

### Why we keep `source_slide_index` instead of duplicating slides into the schema

The schema is metadata. The actual slide XML stays in the source `.pptx` and
is cloned at composition time using python-pptx + (when needed) raw XML
manipulation. This means:

- The schema file stays small and human-readable
- Designers can update the `.pptx` without touching the schema, as long as
  shape names + positions don't drift
- The same skill works for any future `.pptx` template — only the schema
  values change

---

## Authoring procedure

Follow these steps in order. Each step has a verification criterion.

### Step 1 — Inventory every slide

Open the `.pptx` with python-pptx and list all slides with their layout name,
shape count, and visible text. Output as a markdown table you'll annotate.

For each slide, classify into exactly one of:

- `R` — Reusable. Strong brand identity, fixed structure, model clones it.
- `G` — Generated. Variable structure (count of items varies), renderer
  builds it from a `content_type`.
- `S` — Skip. Slide is present in template but not used by PowerGen
  (e.g. a placeholder example slide, a draft).

**Verification:** every slide has exactly one letter. If you're unsure
between R and G, ask: "if the user has 2x the content, does this slide grow
or do I need a second slide?" Grows → G. Need second slide → R.

### Step 1.5 — Apply the overfitting filter to every `R`

For each slide marked `R`, run two yes/no checks:

1. **Reuse check** — does this slide (or one structurally identical to it)
   appear ≥2 times in this template OR plausibly in other templates of the
   same family?
2. **Complexity check** — would the existing renderers (`bullet`, `numbered`,
   `card`, `flow`, `text_block`) plus design tokens fail to reproduce ≥90%
   of this slide's visual?

Then assign tier:

- ✅ Both yes → `reuse_tier: "pattern"`. Give the slide a generic name
  (`numbered_card_grid_v`, `mentor_profile`, `section_divider`) so it can be
  reused in future template schemas.
- ❌ Reuse no, ✅ complexity yes → `reuse_tier: "template_local"`. Keep the
  reusable but accept that it only lives in this schema. Use a
  template-specific name (`closing_timeline`, `welcome_event_banner`).
- ✅ Reuse yes, ❌ complexity no → **demote to `G`**. Rewrite as a
  `generated_slides` entry pointing at the appropriate content_type.
  Common case: a "list of bullet points" page that someone instinctively
  marked `R` because the visual treatment is brand-consistent — but the
  brand consistency comes entirely from tokens, not from the slide structure.
- ❌ Both no → **demote to `G`** (probably `text_block`), or `S` if it
  shouldn't ship at all.

**Verification:** count your tiers. For a 50-page template, expect roughly
5-10 `pattern` + 0-3 `template_local` + the rest `G` or `S`. Anything more
than ~15 reusables total is a red flag — go back and demote.

### Step 2 — For each `R` slide, identify slots

Open the slide, list every shape with text, and decide which are slots vs
which are fixed decoration. A shape is a slot if and only if its text would
change between two different uses of this template.

For the cover slide: university name, student info, advisor name, semester
title → slots. Background gradient, logo, decorative dots → not slots.

For each slot, record:

- `key` — a stable name you'll use in user-facing JSON. Use snake_case.
- `kind` — text | multiline | repeating | image | optional_hint
- locator — `shape_name` (preferred), or `shape_name` + `nth`, or
  `shape_name` + `near: {top, left}`

**Verification:** if you pick a slot, write down what would happen if it
weren't filled. If the answer is "the template's default text appears" and
that text is brand-correct, the slot is `optional` (set `required: false`).
If the default would be wrong (e.g. shows "王同学" for a different student),
the slot is `required: true`.

### Step 3 — Identify repeating groups

Some `R` slides contain a fixed number of repeating units (the 2-card red-line
grid, the 4-card consequence grid). Don't enumerate every slot manually. Use
a `repeating` slot:

```json
{
  "key": "cards",
  "kind": "repeating",
  "count": 2,
  "max_count": 2,
  "anchor_shape": "圆角矩形 8",
  "stride_y": 2.44,
  "fields": {
    "number": { "shape_name": "文本占位符 9", "kind": "text" },
    "title":  { "shape_name": "文本占位符 12", "kind": "multiline" },
    "body":   { "shape_name": "文本框 19", "kind": "multiline" },
    "footer": { "shape_name": "文本框 5", "kind": "multiline" }
  }
}
```

`count` is how many copies exist in the template. `max_count` caps how many
the renderer will instantiate. `stride_y` is the vertical offset between
copies (in inches), used when the renderer duplicates a group.

**Important caveat:** for v1, `max_count == count`. We do NOT support
"add a 3rd card to a 2-card grid" automatically, because the visual
proportions break. If the user needs more, the LLM should pick a different
slide or use a `G`-type renderer instead. Document this limit in the schema's
`notes` field.

### Step 4 — For each `G` slide, declare a `content_type`

Pick from the closed set: `bullet`, `numbered`, `card`, `flow`, `text_block`.

If a slide doesn't fit any, do NOT invent a new type silently. Either:
- (a) reclassify the slide as `R` and add a slot definition, or
- (b) add the new type to this skill's content_type registry (below) with a
      worked example, and write a renderer for it before shipping.

For each `G` content_type used, record which design tokens it consumes. This
documents the contract between the schema and the renderer.

### Step 5 — Extract design tokens

Open the template, find shapes that visually carry brand identity, read their
fill / font color / font name. Record only what a renderer will consume.

Verify by writing one synthetic generated slide using only the tokens. If it
"looks like" the template (same primary color, same title font), tokens are
sufficient. If it looks generic, you're missing a token.

### Step 6 — Write `template.schema.json`, validate

Write the schema (structure below). Then run the validator script bundled
with this skill (`scripts/validate.py`) which checks:

- every `source_slide_index` exists in the `.pptx`
- every locator (`shape_name`, `nth`, `near`) resolves to exactly one shape
- every accent color is a valid hex
- every `repeating.fields` shape exists in the source slide

---

## Schema structure

```json
{
  "schema_version": "1",
  "template_id": "string, snake_case, globally unique",
  "source_pptx": "relative path to the .pptx file",
  "notes": "free-text caveats for future maintainers",

  "tokens": {
    "primary_color": "#RRGGBB",
    "accent_colors": ["#RRGGBB", "..."],
    "title_font": { "name": "string", "size_pt_range": [min, max] },
    "body_font":  { "name": "string", "size_pt_range": [min, max] },
    "logo_image_ref": { "source_slide_index": int, "shape_name": "string" }
  },

  "reusable_slides": {
    "<slide_key>": {
      "reuse_tier": "pattern | template_local",
      "source_slide_index": int,
      "purpose": "human description, one line",
      "slots": {
        "<slot_key>": {
          "kind": "text | multiline | repeating | image | optional_hint",
          "shape_name": "string",
          "nth": int,                 // optional, for duplicate names
          "near": { "top": float, "left": float },  // optional, fallback locator
          "required": bool,
          "default": "string or null",
          "max_chars": int            // optional, soft cap for renderer warnings
        }
      }
    }
  },

  "generated_slides": {
    "<content_type>": {
      "renderer": "renderer module name",
      "consumes_tokens": ["primary_color", "title_font", "..."],
      "max_items": int,
      "notes": "string"
    }
  },

  "compose_hints": {
    "section_intro_pairs": [
      {"intro": "<reusable_slide_key>", "divider": "<reusable_slide_key>"}
    ],
    "ordering_rule": "free-text guidance for the composer LLM"
  }
}
```

### Field-by-field rationale

- **schema_version** — bump on breaking changes so old schemas can be detected
  and migrated. Start at `"1"`.
- **template_id** — used as a registry key when PowerGen has multiple
  templates installed. Snake_case for filename safety.
- **source_pptx** — relative so the schema + pptx can be moved as a unit.
- **notes** — captures human knowledge that doesn't fit a field. E.g.
  "Designer plans to add a 5th accent color in v2." Saves future you.
- **tokens** — see philosophy above. Minimal, renderer-driven.
- **tokens.logo_image_ref** — points to the actual logo shape in the source
  pptx so the composer can extract the binary at runtime instead of duplicating
  it as a separate file.
- **reusable_slides** — keyed by a *semantic* name (`cover`, `mentor_intro`),
  not by index, so the composer LLM can request slides meaningfully.
- **reuse_tier** — `"pattern"` means this slide structure is generic enough
  to be reused across multiple templates (and its slide_key should be a
  generic name like `numbered_card_grid_v`). `"template_local"` means it's
  reusable within this one template only (template-specific name is fine).
  The composer LLM treats both the same way at runtime; the distinction
  exists for cross-template pattern library curation. See Step 1.5 of the
  authoring procedure for how to assign tier.
- **slot.required** — distinguishes "you MUST provide this or composition
  fails" from "fill if you have it, else leave default/empty".
- **slot.default** — what to fall back to if `required: false` and no value
  given. `null` means "empty the shape".
- **slot.max_chars** — soft cap. Renderer logs a warning when exceeded so
  text overflow can be caught in QA, but doesn't block composition.
- **generated_slides** — declares the contract between schema and renderer.
  When you add a new content_type, you must register it here so the schema
  is self-documenting.
- **generated_slides.max_items** — many layouts visually break beyond a
  certain count (e.g. a card grid above 6 items). Renderer reads this to
  decide when to paginate.
- **compose_hints.section_intro_pairs** — captures pairs like
  ("section_intro_simple slide" + "section_divider 02. slide") that always
  appear together. The composer LLM uses this to avoid splitting them.
- **compose_hints.ordering_rule** — free text. Some templates have a
  conventional order (cover → mentor → section1 → ... → closing). The
  composer respects it.

---

## How the schema is used at runtime

The schema is authored once (per template) and consumed at every PPT
generation. The runtime pipeline has three actors with sharply separated
responsibilities:

### Actor 1: Composer LLM (semantic → structural mapping)

Given the user's prompt + content + the schema, the LLM produces a `plan`
JSON. It is told:

- The list of available `reusable_slides` with their semantic names,
  purposes, and slot keys (NOT the underlying shape names or layout details)
- The list of available `generated_slides` content_types with their
  use-case descriptions and `max_items`
- The `compose_hints.ordering_rule`

The LLM's output is a flat list of slide entries:

```json
{
  "template_id": "lumi_course_planning_v1",
  "slides": [
    { "slide_kind": "reusable", "ref": "cover",
      "fill": { "university": "...", "student_info": "...", ... } },
    { "slide_kind": "reusable", "ref": "section_divider",
      "fill": { "number": "02.", "title_zh": "...", "subtitle_en": "..." } },
    { "slide_kind": "generated", "content_type": "card",
      "fill": { "items": [ {...}, {...}, {...} ] } },
    ...
  ]
}
```

The LLM **does** decide: which slides to include, what order, which content
goes into which slot, when to use a reusable vs a generated slide.

The LLM **does not** decide: colors, fonts, spacing, positions, layout
geometry. None of that is in its input.

This is the crux of why the schema works — the LLM operates on a small,
enumerable decision space (pick from N reusables + M content_types, fill
named slots), not on an open-ended visual design space.

### Actor 2: Composer code (plan → final .pptx)

Pure deterministic Python. For each entry in the plan:

- `reusable` → open `source_pptx`, clone slide at `source_slide_index`,
  walk the slot definitions, resolve each locator (`shape_name` [+ `nth`]
  [+ `near`]), substitute text. Append to output deck.
- `generated` → call `renderers.<content_type>(fill, tokens)`. Renderer
  returns a slide object built from scratch using `python-pptx`, reading
  colors / fonts from the schema's `tokens`. Append to output deck.

No LLM in this loop. Failures are deterministic and debuggable. If a slot
locator fails to resolve, the validator should have caught it at author
time (Step 6).

### Actor 3: Renderers (content_type → slide)

One Python module per content_type. Each renderer:

- Reads the data from `fill` (e.g. `items: [...]` for a card grid)
- Reads its declared tokens from the schema's `tokens` block
- Builds a slide with python-pptx, respecting `max_items` for pagination

Renderers are template-agnostic. The same `card` renderer works against any
template's tokens. This is the second crux: renderers don't know or care
which template they're running under, only what tokens were given to them.

### Why this three-actor split matters

- The LLM is the only non-deterministic actor, and its output (the plan
  JSON) is human-readable and editable. A user can review or hand-edit the
  plan before it's executed. End-to-end LLM PPT generators don't allow this.
- The composer code is testable and debuggable in isolation.
- Renderers can be developed and improved without touching schemas or
  templates.
- A schema bug (bad locator) fails at author time; a content bug (wrong
  text) fails in the plan; a layout bug fails in the renderer. Each layer
  has a single failure mode.

---

## Content type registry (closed set, v1)

| content_type | Use for | Required tokens | Max items | Notes |
|---|---|---|---|---|
| `bullet` | flat list of independent points | primary_color, body_font | 8 | falls back to two-column above 5 |
| `numbered` | ordered steps | primary_color, body_font | 8 | renders 01/02/03 prefix in primary color |
| `card` | 1-N items with same internal structure (e.g. courses) | primary_color, accent_colors[0], title_font, body_font | 6 | one card per slide above 6 |
| `flow` | A → B → C arrow chain | primary_color, accent_colors | 5 | horizontal; vertical variant TBD |
| `text_block` | a paragraph with a heading | primary_color, title_font, body_font | 1 | use sparingly, looks plain |

To add a new content_type: open a PR that updates this table AND ships a
renderer in the same commit. Schemas referencing an unregistered content_type
must fail validation.

---

## Worked example: `test.pptx`

The bundled `examples/test_template.schema.json` is the complete schema for
the included `test.pptx`. Read it alongside this document. Key decisions
made there:

- 11 slides total. After Step 1 inventory: slides 3 and 6 and 8 in
  `test.pptx` are the same `section_intro` layout used three times — they
  collapse to one reusable entry. Same idea: slide 10 is the
  `section_divider` layout (it appears once in `test.pptx` but four times
  in `generated.pptx`). After dedup: 7 distinct reusable slides.
- Step 1.5 tier assignment:
  - `cover`, `mentor_intro`, `section_intro`, `section_divider` →
    `reuse_tier: "pattern"` (high reuse + high complexity, generic enough
    to carry across templates of this family)
  - `red_line_grid_2`, `consequence_grid_4` → also `reuse_tier: "pattern"`
    but renamed in this revision from their original literal names. The
    layouts are generic numbered-card grids; their *content* in this
    template happens to be about red lines and consequences, but the
    structure is reusable. Keys become `numbered_card_grid_v` and
    `numbered_card_grid_h`.
  - `closing_timeline` → `reuse_tier: "template_local"`. The timeline
    graphic is specific to this template; we don't expect to encounter it
    elsewhere.
- `cover` has 4 slots. Two shapes both named `TextBox 15` resolved using
  `nth: 0` (student) and `nth: 1` (advisor).
- `numbered_card_grid_v` (formerly `red_line_grid_2`) uses a `repeating`
  slot with `count: 2, max_count: 2` and a note that this layout cannot
  extend beyond 2 cards.
- `numbered_card_grid_h` (formerly `consequence_grid_4`) uses `repeating`
  with `count: 4, max_count: 4`. The per-card accent color is read from
  `tokens.accent_colors` by index, so card 0 is `#7578EC`, card 1 is
  `#F7B802`, etc.
- `closing_timeline` has an `optional_hint` slot for the
  "老师请介绍...（阅后删除）" placeholder.
- Tokens extracted: 1 primary (TBD — needs designer input), 4 accents (read
  directly from slide 5), title font + body font from observed runs.

---

## Anti-patterns to avoid

1. **Marking every slide as a reusable** — the schema is not a copy of the
   `.pptx`. If you've ended up with 30 reusables for a 50-page template,
   you've reproduced the source file in JSON form. Run Step 1.5 again and
   demote aggressively. The whole point of `generated_slides` is to absorb
   the long tail of "looks unique but is really just a list with brand
   styling".
2. **"Just add a `style` field"** — schemas creep when authors add fields
   "in case a renderer needs it later". Don't. Add fields when a renderer
   demands them.
3. **Auto-extracting every shape as a slot** — most shapes are decoration.
   Slots are specifically the things that change between uses.
4. **Letting `nth` indices proliferate** — if a slide has 5+ slots all
   identified by `nth`, the designer should rename the shapes. File a bug
   against the `.pptx`, don't paper over it in the schema.
5. **Mixing R and G in one slide** — a slide is either fully cloned-and-filled
   or fully generated. If you're tempted to "clone the header but generate
   the body", split it into two slides or promote the body to a `repeating`
   slot.
6. **Using `optional_hint` as a TODO list** — `optional_hint` is for
   instruction-to-user text baked into the template. If the slot just has a
   reasonable default (e.g. "Insert your university name"), use `default`
   instead.

---

## Files in this skill

- `SKILL.md` — this file
- `examples/test_template.schema.json` — full worked example for `test.pptx`
- `scripts/validate.py` — schema validator (checks locators resolve, hex
  colors valid, content_types registered)
- `scripts/inspect_pptx.py` — helper to dump shape inventory from a `.pptx`,
  use as the first step when authoring a new schema
