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

## ~~Layer 2 — Template-Based / markitdown approach (Abandoned)~~

> **Abandoned**: `template_filler.py` and `prompts_template.py` deleted. Root cause: markitdown extracts flat text with no shape identity — duplicate shape names collide, repeating groups cannot be expressed, decoration cannot be distinguished from slots. String-match replacement is fragile and non-deterministic. Replaced by schema-based approach below.

~~**Workflow**: markitdown → LLM analysis (slide_relevant + text node classification) → LLM mapping (replacement text) → python-pptx paragraph replacement~~

~~**Why it failed**: shape name collisions (`TextBox 15` × 2 on cover), no concept of slot kind (text vs repeating vs optional_hint), LLM sees flat text dump with no structure — output quality is unpredictable and breaks on any template with non-trivial layout.~~

---

## Layer 2 — Schema-Based Template Composition (In Progress)

**Goal**: Template-driven output with predictable, brand-consistent results. Visual design is fully frozen in the template; the LLM only decides *what content goes where*, not how it looks.

**Use case**: User provides a branded `.pptx` template with a co-located `template.schema.json`. Powergen composes a new deck by cloning reusable slides (filling named slots) and generating variable-content slides (via typed renderers reading design tokens).

**Why different from the abandoned approach**

| | markitdown (abandoned) | schema-based (new) |
|---|---|---|
| Shape identity | flat text, no names | composite locator (`shape_name` + `nth` + `near`) |
| Slot semantics | none — every text node is equal | typed (`text`, `multiline`, `repeating`, `image`, `optional_hint`) |
| LLM decision space | open-ended text replacement | pick from N reusables + M content_types, fill named slots |
| Variable-length content | impossible | `generated_slides` with typed renderers |
| Brand consistency | depends on LLM | frozen in template + design tokens |

**Three-actor architecture**

1. **Composer LLM** — reads schema's semantic surface (slide names, slot keys, content_type descriptions), produces a flat `plan.json`. Decides *which* slides and *what* content. Does NOT see colors, fonts, positions.
2. **Composer code** — deterministic Python. For each plan entry: clones slide from source `.pptx` and fills slots (reusable), or calls renderer with tokens (generated).
3. **Renderers** — one module per `content_type`. Template-agnostic. Read only `fill` data + design tokens.

**Schema concepts** (see `layer2/SKILL.md` for full spec)
- `reusable_slides` — slides to clone verbatim and fill (cover, section dividers, mentor profile, card grids)
- `generated_slides` — variable-length content built from scratch by a renderer (`bullet`, `numbered`, `card`, `flow`, `text_block`)
- `reuse_tier` — `"pattern"` (generic, reusable across templates) vs `"template_local"` (only in this schema)
- Slot locators — `shape_name` only → `+ nth` → `+ near {top, left}` (in order of preference)
- Design tokens — minimal: 1 primary color, 2–4 accents, title font, body font, logo ref

**Tooling**
- Library: `python-pptx` (slide cloning via raw XML + python-pptx)
- Model: `claude-haiku-4-5` (Composer LLM call is small: schema surface + user content)
- Schema: `layer2/schemas/<template>.schema.json` (authored once per template)
- Validator: `layer2/scripts/validate.py` (checks locators resolve, hex colors valid, content_types registered)

**Deliverables**

| File | Purpose | Status |
|---|---|---|
| `layer2/SKILL.md` | Schema authoring procedure (6 steps) | Done |
| `layer2/schemas/test_template.schema.json` | Worked example for `test.pptx` | Done |
| `layer2/scripts/validate.py` | Schema validator (checks locators, hex, content_types) | Done |
| `layer2/scripts/inspect_pptx.py` | Dump shape inventory from `.pptx` | Done |
| `layer2/composer/schema_loader.py` | Load + strip comments from schema JSON | Done |
| `layer2/composer/slot_resolver.py` | Resolve `shape_name` / `nth` / `near` locators | Done |
| `layer2/composer/slide_cloner.py` | Clone reusable slide + fill all slot kinds | Done |
| `layer2/composer/renderers/card.py` | `card` content_type renderer | Done |
| `layer2/composer/renderers/bullet.py` | `bullet` content_type renderer | Done |
| `layer2/composer/renderers/flow.py` | `flow` content_type renderer | Done |
| `layer2/composer/schema_gen.py` | **Local** pptx → schema extraction (no LLM, cached) | Done |
| CLI: `powergen template --pptx` | Auto-schema pipeline (`--pptx` or `--schema`) | Done |

**Known issues / next polish**

| Issue | Symptom | Likely cause |
|---|---|---|
| Slot fill failures on some slides | Original template text shows through | PLACEHOLDER shapes not resolved after clone — spTree deep-copy may not include layout-inherited placeholders |
| Font / formatting degradation | Text loses template font; falls back to system default | Theme font refs (`+mj-lt`, `+mn-lt`) don't resolve without original slide layout relationship in cloned slide |
| Bullet formatting off | Bullet character mispositioned or missing | `_set_multiline` doesn't copy `<a:pPr>` (paragraph properties including indent/bullet settings) |

**Validation (what exists now)**

```bash
python -m powergen.layer2.scripts.validate powergen/layer2/schemas/test_template.schema.json
```

---

## ~~Future Optimization — XML Pattern Extraction (superseded)~~

> **Superseded**: The idea of extracting a lightweight schema from XML at runtime is now captured more rigorously in the static `template.schema.json` approach. Runtime XML extraction is replaced by the one-time `SKILL.md` authoring procedure.

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

**Status**: Not started. Requires Node.js toolchain and pptxgenjs integration.

---

## Token cost reference

| Operation | Model | Approx. cost |
|-----------|-------|-------------|
| Layer 1 full run (create + approve + render) | Haiku | ~$0.002 |
| Layer 2 schema composition (full deck) | Haiku | ~$0.005–0.02 |
| Layer 3 full run | Sonnet | ~$0.05–0.20 |
| **Any layer, `--mock` flag** | none | **$0.00** |

Always use `--mock` for code path verification. Reserve real API calls for validating prompt quality and output content.

---

## Summary

| Layer | Model | Relative Cost | Human Touch Needed | Status |
|-------|-------|--------------|-------------------|--------|
| 1 — Scaffold | Haiku | $ | Significant | In progress (~70%) |
| 2 — Schema composition | Haiku | $ | Minimal | Schema done, composer not started |
| 3 — Full Visual | Sonnet | $$$ | 1-2 steps | Not started |
