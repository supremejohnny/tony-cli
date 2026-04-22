# Powergen Architecture

## Three-Layer Overview

PowerGen generates presentations at three fidelity levels. Each layer is independently useful.

| Layer | Goal | Model | Status |
|-------|------|-------|--------|
| 1 — Scaffold | Structural skeleton for human post-processing | Haiku | In progress |
| 2 — Schema Composition | Template-driven, brand-consistent output | Haiku | In progress |
| 3 — Full Visual | Presentation-ready, minimal polish needed | Sonnet | Not started |

---

## Layer 1 — Scaffold

Two LLM calls: plan generation → spec generation. Renderer is pure code (zero tokens).

**Spec design**: only `title`, `bullets`, `layout name`, `speaker notes`. No colors/fonts/visuals.
Layouts: Title Slide, Title and Content, Section Header, Two Content, Blank.

**Mock testing** (zero tokens):
```bash
powergen --mock create "topic" && powergen --mock approve && powergen --mock render
```

---

## Layer 2 — Schema-Based Template Composition

### Why not markitdown (abandoned)

markitdown extracts flat text with no shape identity. Duplicate shape names collide, repeating groups can't be expressed, decoration vs slot is indistinguishable. String-match replacement is fragile and non-deterministic. `template_filler.py` and `prompts_template.py` deleted.

### Why not runtime XML extraction (superseded)

Runtime XML extraction replaced by static `template.schema.json` + one-time SKILL.md authoring procedure. More predictable, cacheable, reviewable.

### Three-Actor Model

1. **Composer LLM** — reads schema's semantic surface (slide names, slot keys, original text). Outputs a flat `plan.json`. Does NOT see colors/fonts/positions.
2. **Composer code** — deterministic Python. For each plan entry: clones reusable slide + fills slots, or calls renderer with design tokens.
3. **Renderers** — one module per `content_type` (card, bullet, flow). Template-agnostic. Read only `fill` data + design tokens.

### Schema Concepts

- `reusable_slides` — slides to clone verbatim and fill (cover, section dividers, profile, card grids)
- `generated_slides` — variable-length content built from scratch by a renderer
- `reuse_tier` — `"pattern"` (generic, reusable across templates) vs `"template_local"`
- Slot locators — `shape_name` → `+ nth` → `+ near {top, left}` (in order of preference)
- Design tokens — minimal: 1 primary color, 2–4 accents, title font, body font, logo ref
- Auto-schema (`schema_gen.py`) — local extraction from any pptx, no LLM, cached as `<pptx>.schema.json`

---

## Layer 3 — Full Visual (Planned)

- Library: `pptxgenjs` (Node.js)
- Model: `claude-sonnet-4-6` or higher
- QA: `soffice` → `pdftoppm` → visual inspection loop
- Workflow: plan → design spec (palette, font pair, per-slide layout) → code generation → execute → QA loop

---

## Token Cost Reference

| Operation | Model | Approx. cost |
|-----------|-------|-------------|
| Layer 1 full run | Haiku | ~$0.002 |
| Layer 2 schema composition (full deck) | Haiku | ~$0.005–0.02 |
| Layer 3 full run | Sonnet | ~$0.05–0.20 |
| Any layer, `--mock` flag | none | $0.00 |
