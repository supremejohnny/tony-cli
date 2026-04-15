# Powergen Development Roadmap

Three-layer architecture for progressive PPT generation capability.
Each layer is independently useful and builds toward the next.

---

## Layer 1 — Scaffold (Current)

**Goal**: Lowest token cost. Produces a clean structural skeleton for human post-processing.

**Use case**: Quick report framework, meeting outline, internal draft — output is meant to be refined by hand.

**Tooling**
- Library: `python-pptx`
- Model: `claude-haiku-4-5` (cheapest)
- Scripts: existing `powergen/` modules (cli, planner, spec_builder, renderer)

**Spec design**
- Only: `title`, `bullets`, `layout name`, `speaker notes`
- No colors, fonts, or visual elements
- Layouts limited to generic names: Title Slide, Title and Content, Section Header, Two Content, Blank

**Token strategy**
- Minimal system prompts
- Two LLM calls: plan generation → spec generation
- Renderer is pure code (zero LLM tokens)

**Status**: ~70% complete.

Remaining work:
- Prompt iteration based on real API responses (observe actual model output, identify failure patterns, tighten constraints)
- Spec schema refinement (better layout naming, more expressive bullet structure)
- Render layer diversity — add support for new slide types beyond title+bullets:
  - Comparison / two-column (side-by-side contrast)
  - Section divider
  - Stats / number callout
  - (others as identified during prompt iteration)

**Mock testing (zero tokens)**

```bash
# CLI mode
powergen --mock create "your topic"
powergen --mock approve
powergen --mock render
```

```
# REPL mode
powergen --mock
/create your topic
/approve
/render
```

Mock returns hardcoded plan/spec JSON. The rendered `.pptx` will be a real file with canned content ("The Future of AI Development" etc.) — this is expected. Use to verify the code path works end-to-end without spending tokens.

---

## powergen distill (Complete — initial implementation)

Converts workspace files (`.pptx`, `.pdf`, `.docx`, `.md`, `.txt`) into structured `.distill.json` knowledge chunks stored in `.powergen_distill/`. Provides a persistent context layer for `create` and `template`. Hash-based caching means re-runs are free for unchanged files. `template` runs distill automatically as a pre-step.

→ See [`.powergen_skill/distill.md`](.powergen_skill/distill.md) for full schema, step-by-step execution, and architecture notes.

---

## Layer 2 — Template-Based (Complete — initial implementation)

**Goal**: Template-driven output. Model handles content only; all visual design comes from the template.

**Use case**: User provides a branded or styled `.pptx` template. Powergen fills in the content. Near-zero design work required from AI.

**Tooling**
- Library: `python-pptx` (paragraph-level text replacement, preserves run formatting)
- Model: `claude-haiku-4-5` (task is just text substitution)
- Content extraction: `markitdown` to read template text structure

**Actual implementation** (differs from original plan)

The original plan used unpack → XML edit → pack. This was replaced with direct `python-pptx` manipulation because:
- XML approach: text split across multiple `<a:t>` runs → matching fails
- python-pptx `para.text` concatenates all runs natively → correct matching
- Eliminated encoding issues and 3-minute XSD validation delays

**Workflow**
1. Run `markitdown` on template → extract text per slide
2. LLM call 1 (analysis): classify each slide as `slide_relevant: true/false` and each text node as `title / body / bullet / skip`
3. LLM call 2 (mapping): for all non-skip nodes on relevant slides, generate replacement text proportional in length to original
4. Apply mappings via python-pptx: match paragraph text, replace first run, blank remaining runs (preserves visual formatting)
5. Save output as `<template>-filled.pptx`

**Key features**
- Fuzzy template selection: when multiple `.pptx` files are in the workspace, difflib matches the user's brief text against template filenames (typo-tolerant, cutoff 0.6)
- Slide relevance filter: slides marked `slide_relevant: false` (e.g. template instructions, navigation placeholders) are skipped entirely — original content preserved
- Safety net: even if the LLM generates mappings for irrelevant slides, the code-level filter catches them

**Status**: Complete (initial implementation). Validated with real Haiku API — correct content replacement, visual styles preserved, irrelevant slides untouched.

**Known next steps**
- `/template-revise "feedback"` command: re-run mapping with original brief + revision feedback appended (stateless, one extra API call)
- Pass brief to Call 1 (analysis): allows `slide_relevant` decisions to be contextually aware, not just structural; enables per-slide `content_hint` for richer mapping
- Workspace content utilization: distill results from `.powergen_distill/` are now available as structured context for Call 2 (implemented via distill pre-step)

**Mock testing (zero tokens)**

```bash
# CLI mode
powergen --mock template "your brief"
```

```
# REPL mode
powergen --mock
/template your brief
```

Mock returns a 3-slide canned analysis (slide 2 marked `slide_relevant: false`) and a mapping that intentionally includes a slide 2 entry to exercise the safety filter. Expected output:

```
Template: <your-template>.pptx
[1/3] Analysing template structure…
[2/3] Generating content mapping…
  Skipping slide 2 (not relevant).    ← confirms filter works
[3/3] Applying replacements…
  Warning: text not found in slide 1: 'Presentation Title'   ← expected, mock uses fake text
  Warning: text not found in slide 3: 'Slide Heading'        ← expected
Done: <your-template>-filled.pptx
```

The warnings are expected and correct — mock text nodes ("Presentation Title" etc.) won't match any real template content. The important signal is `Skipping slide 2 (not relevant).`

**Important: mock detection uses `system_prompt` only**

The content mapping call passes the full analysis JSON in `user_prompt`, which contains the string `"text_nodes"`. If mock detection checked `combined = system_prompt + user_prompt`, the second call would falsely match the analysis condition and return the wrong JSON (causing `mappings = []` and silent no-op). Detection therefore checks `system_prompt.lower()` only for Layer 2 responses.

---

## Future Optimization — XML Pattern Extraction (Token Reduction)

**Idea**: Instead of passing raw XML or full slide text to the LLM, pre-process the template locally to extract a structured schema, then send only the schema.

**How it works**
1. Use `scripts/office/unpack.py` to unpack the `.pptx` into raw XML
2. Local Python parses the XML and extracts a lightweight schema per slide:
   - Layout type (title page / two-column / content / blank etc.)
   - Placeholder types and positions (`ph type`, `ph idx`)
   - Text hierarchy levels (title / subtitle / bullet depth)
   - Recurring style patterns (font, size, color groupings)
3. Send only the schema JSON to the LLM — not the full XML or raw text
4. LLM fills content against the schema
5. Use `scripts/office/pack.py` to write content back into XML and repack

**Expected benefit**
- Token reduction: ~80–90% vs sending full XML
- This is the scenario where `scripts/` becomes a core pipeline component rather than dead code
- Pairs naturally with the multi-template merging use case (extract schemas from multiple templates, let LLM decide which sections to take from which)

**Dependencies**
- Requires `scripts/office/unpack.py` and `pack.py` to be integrated into the main workflow
- Needs a schema extraction module (new, ~100–150 lines of Python)
- `scripts/office/validate.py` can then gate the final output for correctness

**Status**: Not started. Low priority until Layer 3 is underway, but the schema extraction module could be prototyped independently.

---

## Layer 2.5 — Pattern Catalog Pipeline (Implemented, Architecture Under Review)

**Goal**: Replace the fuzzy text-replacement approach of Layer 2 with a structured, slot-aware pipeline that knows the semantic purpose of each shape.

**What was built**

Three-phase pipeline on top of the template PPTX:

1. **Phase 1 — Catalog** (`powergen catalog`): Analyzes a template PPTX and produces a `*.catalog.json` describing each slide as a reusable pattern with named slots (keyed by `shape_name`), `fit_for`/`not_fit_for` metadata, and deduplication of structurally identical slides.

2. **Phase 2 — Planner** (`powergen fill "<brief>" --plan-only`): Given a user brief + distill context, selects which patterns to use and generates slot content — a structured plan JSON.

3. **Phase 3 — Filler** (`powergen fill "<brief>"`): Deep-copies template slides, rewrites text at the `<a:p>` XML level (preserving run formatting), reorders/prunes slides, and saves output.

**Status**: Implemented and API-tested on a real university course-selection template (11 slides → 9 deduplicated patterns). Commits: `b8d9953` (catalog), `cb727b4` (planner + filler).

---

### Open Design Problem: Template-Bound Patterns

**Problem statement**

The current pipeline is entirely **template-bound**: every pattern in the output must correspond to a slide that physically exists in the template PPTX. The Planner can only choose from patterns the Catalog found; the Filler can only write into shapes that already exist on those slides.

This creates a hard constraint: the creative range of the generated output is limited to whatever slide layouts the template author happened to include. A template with 9 patterns can only produce presentations that are remixes of those 9 layouts — even if the content would be better served by a simpler or completely different arrangement.

**Human designer analogy**

A human designer using a branded template does not feel this constraint. They treat the template as a **visual theme** (color palette, typography, background decorations, icon style) and compose slide layouts freely:

- Need a single callout statement? Create a new slide with one large text box, styled to match.
- Need a two-column comparison? Build it from scratch using the template's colors and fonts.
- Need a numbered list with icons? Arrange shapes manually — no equivalent slide needs to exist in the template.

Only a handful of slides (cover, section dividers, bio page) are truly "fixed" and borrowed as-is from the template.

**Implications for the current architecture**

| Current approach | Desired behavior |
|---|---|
| Pattern = a full slide copied from template | Pattern = a layout recipe that can be instantiated fresh |
| Filler writes into pre-existing shapes | Filler creates new shapes with template-derived styling |
| Visual range = {slides in template} | Visual range = {any layout composable from theme tokens} |
| Adding a new layout requires editing template PPTX | New layouts emerge from prompt + theme tokens alone |

**What would need to change**

1. **Theme token extraction**: Instead of cataloging slide structures, extract visual primitives from the template — background fills, primary/secondary/accent colors, heading/body font families, sizes, and weights, border/shadow styles used on shapes.

2. **Layout grammar**: Define a small set of abstract layout types (single-hero, two-column, grid-N, timeline, table, cover, section-divider) that the Planner can request by name, independent of what the template contains.

3. **Dynamic shape creation**: The Filler generates new slides from scratch using `python-pptx`, applying theme tokens to newly created shapes rather than writing into pre-existing ones.

4. **Template = style source, not structure source**: The template PPTX is consulted only to extract visual style; its slide structure is ignored for generation purposes (though it could still be used for a few "fixed" slides like the cover).

**Discussion deferred**: This is a significant architectural rethink. The current Phase 1–3 implementation remains as a reference and proof-of-concept for the slot-filling mechanics. The theme-token + dynamic-layout approach will be designed separately before implementation begins.

---

### Attempt: `generate` command — Typed Content + Canvas Cloning (Implemented, Unsatisfactory)

**Goal**: Decouple content generation from template structure. Claude generates a typed slide plan using a fixed 7-type vocabulary; a dynamic renderer creates slides from scratch decorated with the template's visual identity.

**What was built** (commits on `dev/powergen`)

- `powergen/content_generator.py` + `prompts_content_generator.py`: Claude generates a typed plan (`title`, `section_divider`, `content_simple`, `content_structured`, `two_column`, `timeline`, `special`). Prompt includes pptx-skill design rules (layout variety, content_structured variant selection, etc.).
- `powergen/theme_extractor.py`: Extracts theme tokens (`bg_color`, `accent_color`, `heading_font`, `body_font`) directly from `ppt/theme/theme*.xml` inside the PPTX ZIP — avoids heuristic shape scanning which silently returns defaults when shapes use theme color references.
- `powergen/dynamic_renderer.py`: For each generic slide, clones a template content slide as a "visual canvas" (copies decorative shapes + background, removes all text-bearing shapes), then places text boxes on top. Special slides (title, profile) are taken from template and slot-filled as before. `_reorder_slides` handles final ordering.
- Catalog simplified to v2 schema: `theme` + `special_slides` (reusable:false only). Old `fill` command preserved.

**What works**
- Content generation quality is good: diverse slide types, design rules followed, correct language.
- Theme token extraction is reliable (fixed from heuristic to XML-based).
- Special slides (title) are correctly taken from the template and filled.
- Template's decorative shapes (logo, colored bars, dot patterns) do appear on generated slides after the canvas cloning fix.

**What doesn't work — the fundamental problem**

The canvas cloning approach exposed a mismatch that cannot be resolved with the current architecture:

> **The template's decorative shapes occupy specific zones of the slide. Our text boxes are placed at hardcoded coordinates. These two systems have no awareness of each other.**

Concrete failure modes observed:

1. **Coordinate blindness**: A template may have a colored header bar at `top=0, height=1.2"` and a content area below. Our title text box is placed at `MARGIN=0.5"` — which lands inside the colored bar and overlaps it correctly by accident. But our content starts at `title_bottom + GAP`, which may collide with a template shape sitting at a fixed y-position.

2. **Section divider visual clash**: `_render_section_divider` explicitly overrides the slide background with a dark color. But the cloned canvas still contains the template's decorative shapes (colored rectangles, images) — these were designed for a light-background content slide, not a dark section divider. Result: wrong visual combination.

3. **No content safe zone**: We don't know where on the cloned slide it's safe to write. The template may have a footer strip, a side margin decoration, or a full-bleed image that consumes areas we're writing into.

4. **Font/size mismatch**: Our hardcoded font sizes (40pt title, 15pt body) may not match the template's visual rhythm. A template designed with 28pt titles and tight line spacing will look wrong with our 40pt titles.

**Why the problem is harder than it looks**

The root cause is that "template visual identity" is not just a set of tokens (colors, fonts) — it's a **spatial layout**: which zone is the title zone, which zone is the content zone, where the decorations live, and how much space is left for content.

Extracting this spatial layout reliably from an arbitrary PPTX would require:
- Identifying the "safe content area" on each slide (bounding box not covered by decorative shapes)
- Understanding which shape is a header vs. footer vs. side decoration
- Knowing the template's intended font sizes (not just what fonts exist, but what size they used for each role)

This is non-trivial heuristically and likely requires LLM analysis of the template (vision or structured XML interpretation).

**Paths forward (not yet chosen)**

| Option | Description | Trade-offs |
|---|---|---|
| A. Spatial layout extraction | LLM or vision analyzes the template's content area, outputs `content_zone: {left, top, width, height}` | Requires LLM pass on template; fragile for complex layouts |
| B. Use template layouts as named regions | Map slide types to layout names ("blank", "title and content", etc.); use placeholder positions as content zone | Limited to templates with well-named layouts; some templates break this |
| C. Full visual render (no template canvas) | Abandon template canvas cloning; render purely from theme tokens (color, font) into a blank slide | Loses logo, decorative shapes; output looks generic |
| D. Render into template placeholders | For each generic slide, pick the best-matching template layout, fill its placeholders | Re-introduces template-bound constraint |
| E. Hybrid: minimal canvas + injection zones | Catalog explicitly annotates `content_zone` per slide type during catalog phase (LLM + vision); renderer respects these zones | Adds catalog complexity; likely the most correct approach |

**Recommended next design step**: Option E — extend the catalog phase to output a `content_zone` per representative slide, so the renderer knows exactly where to write. This requires one vision/analysis LLM call during `powergen catalog`, producing `{title_zone, body_zone}` in the catalog JSON.

---

## Layer 3 — Full Visual (Future)

**Goal**: Presentation-ready output requiring 1-2 steps of human polish at most.

**Use case**: Client-facing deck, pitch deck, polished report — output is close to final.

**Tooling**
- Library: `pptxgenjs` (Node.js) — richer visual control than python-pptx
- Model: `claude-sonnet-4-6` or higher
- QA: convert to images via `soffice` + `pdftoppm`, visual inspection loop
- Icons: `react-icons` → rasterized PNG via `sharp`

**Design system (injected into prompt)**
- Color palette selection from named themes (Midnight Executive, Coral Energy, etc.)
- Font pairing rules (header font + body font)
- Layout variety requirements: two-column, icon+text rows, stat callouts, half-bleed image
- Per-slide visual element requirement (no text-only slides)
- Avoid list: no repeated layouts, no centered body text, no accent lines under titles

**Workflow**
1. Plan generation (same as Layer 1)
2. Design spec: model selects color palette, font pair, and per-slide layout type + visual element
3. Code generation: model writes `pptxgenjs` script implementing the full design spec
4. Execute script → render `.pptx`
5. QA loop: convert to images → visual inspection → fix → re-verify

**Token strategy**
- Multiple LLM calls (plan, design spec, code gen, QA)
- Higher model tier required
- QA loop may add 1-3 extra calls depending on issues found

**Status**: Not started. Requires Node.js toolchain and pptxgenjs integration.

---

## Token cost reference

| Operation | Model | Approx. cost |
|-----------|-------|-------------|
| Layer 1 full run (create + approve + render) | Haiku | ~$0.002 |
| Layer 2 template fill (3-slide template) | Haiku | <$0.001 |
| Layer 2 template fill (20-slide template) | Haiku | ~$0.01 |
| Layer 3 full run | Sonnet | ~$0.05–0.20 |
| **Any layer, `--mock` flag** | none | **$0.00** |

Always use `--mock` for code path verification. Reserve real API calls for validating prompt quality and output content.

---

## Summary

| Layer | Model | Relative Cost | Human Touch Needed | Status |
|-------|-------|--------------|-------------------|--------|
| 1 — Scaffold | Haiku | $ | Significant | In progress (~70%) |
| 2 — Template | Haiku | $ | Minimal | Complete (initial) |
| 3 — Full Visual | Sonnet | $$$ | 1-2 steps | Not started |

**Development order**: Layer 1 → Layer 2 → Layer 3
