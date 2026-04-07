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
