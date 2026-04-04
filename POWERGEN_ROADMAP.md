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

---

## Layer 2 — Template-Based (Next)

**Goal**: Template-driven output. Model handles content only; all visual design comes from the template.

**Use case**: User provides a branded or styled `.pptx` template. Powergen fills in the content. Near-zero design work required from AI.

**Tooling**
- Library: `python-pptx` XML layer (unpack → edit → pack)
- Model: `claude-haiku-4-5` (task is just text substitution)
- Reference: `pptx skill` unpack/pack workflow (`scripts/office/unpack.py`, `clean.py`, `pack.py`)
- Content extraction: `markitdown` to read template structure

**Workflow**
1. Unpack template `.pptx` to XML
2. Run `markitdown` on template → extract text structure and placeholder map
3. Single LLM call: generate content mapping (slot → replacement text)
4. Apply mapping: Edit XML text nodes only, no structural changes
5. Pack back to `.pptx`

**Spec design**
- Input: template file + content brief
- Model output: flat key-value map of placeholder → new text
- No layout decisions, no design decisions

**Token strategy**
- One LLM call for content mapping
- Mechanical XML replacement (zero LLM tokens)
- Cheaper than Layer 1 in practice because model has no structural decisions to make

**Status**: Not started. Depends on integrating pptx skill scripts.

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

## Summary

| Layer | Model | Relative Cost | Human Touch Needed | Status |
|-------|-------|--------------|-------------------|--------|
| 1 — Scaffold | Haiku | $ | Significant | In progress |
| 2 — Template | Haiku | $ | Minimal | Not started |
| 3 — Full Visual | Sonnet | $$$ | 1-2 steps | Not started |

**Development order**: Layer 1 → Layer 2 → Layer 3
