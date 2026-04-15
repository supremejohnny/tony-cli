# claude-progress.md

<!--
PURPOSE OF THIS FILE
====================
This is a session log, not an architecture document.
POWERGEN_ROADMAP.md is the architecture document — keep those concerns there.

This file records:
  - What was tried each session
  - What failed and WHY (especially dead ends — do not revisit without new information)
  - Decisions that were made and their rationale
  - The entry point for the next session

IMPORTANT READING INSTRUCTIONS
- Before starting any implementation work, read the most recent session entry.
- If a section is marked [DEAD END — DO NOT REVISIT], do not reopen that investigation
  unless you have concrete new information that changes the constraint.
- Relative dates are always converted to absolute (YYYY-MM-DD) so entries remain
  interpretable after time passes.
-->

---

## Session 2026-04-14

### Context
Learned about harness engineering patterns. Evaluated powergen's readiness for harness.
Decision: don't build full harness yet — architecture still drifting. Instead, lock known
failures first. This file is the first artifact of that decision.

### What was tested
`powergen generate` — the command that attempts to:
1. Generate a typed slide plan (Claude output quality: good)
2. Clone template slides as "visual canvas" for generic slides
3. Render text content on top of the canvas
4. Reorder/prune output to only planned slides

### User-observed failures
- Generated content quality: OK
- Template visual integration: broken in multiple ways (see bugs below)
- Template slides not being removed from output: confirmed

---

### [DEAD END — DO NOT REVISIT] Bug A: Template slides not removed from output

**File**: [powergen/dynamic_renderer.py](powergen/dynamic_renderer.py) line 464

**What happens**:
```python
shutil.copy2(str(template_path), str(output_path))  # seeds output with ALL template slides
prs = Presentation(str(output_path))
```
The output file starts as a full copy of the template (e.g. 11 slides).
New slides are appended (indices 11, 12, …). Then `_reorder_slides` is called to prune.

**Why pruning silently fails**:
`_reorder_slides` ([powergen/catalog_filler.py](powergen/catalog_filler.py) line 113) calls:
```python
prs.part.drop_rel(rId)
```
If `Part.drop_rel` is unavailable in the installed python-pptx version, this raises
`AttributeError` which is swallowed by `except Exception: pass` (line 136).
Result: ALL original relationship entries survive → output contains all original template
slides + newly generated ones.

**Confirmed pattern**: User observed that template slides are not deleted from the output.

**Root cause**: The design of seeding output from `shutil.copy2` is inherently fragile.
The correct approach is to build output from an empty `Presentation()` and only copy
the specific slides needed — never start from a copy of the template.

**Do not attempt**: patching `drop_rel` call or adding version checks. The seeding
approach is wrong at the design level.

---

### [DEAD END — DO NOT REVISIT] Bug B: Canvas cloning has no spatial awareness

**File**: [powergen/dynamic_renderer.py](powergen/dynamic_renderer.py) `_clone_slide_as_canvas` (line 132)

**What happens**:
The function copies all non-text shapes from a template slide to a new blank slide,
then the renderer places textboxes at hardcoded coordinates:
- `MARGIN = Inches(0.5)` from slide edge (line 21)
- Title at `(MARGIN, MARGIN)` — top-left corner
- Content starts at `MARGIN + Pt(FONT_TITLE_PT).emu + GAP*2`

**Why this is broken**:
Template decorative shapes (logo, colored header bar, side decoration, footer strip)
occupy specific zones at fixed positions. Our textboxes have no knowledge of these zones.
- A template with a header bar at `top=0, height=1.2"` → our title at `MARGIN=0.5"`
  lands inside the bar (may look OK by accident, or may not)
- A colored side column → our full-width content box writes over it
- A footer strip → our content box extends into it

There is no "safe content area" computed anywhere. The two coordinate systems are
completely blind to each other.

**Do not attempt**: adding more margin/padding heuristics. The problem is structural —
we need the template to explicitly declare its content zone. See POWERGEN_ROADMAP.md
Option E (content_zone in catalog) for the correct path forward.

---

### [DEAD END — DO NOT REVISIT] Bug C: Section divider visual clash

**File**: [powergen/dynamic_renderer.py](powergen/dynamic_renderer.py) `_render_section_divider` (line 198)

**What happens**:
The section divider type calls `_set_slide_background(slide, div_bg)` to apply a
dark background color. But the slide was created via `_clone_slide_as_canvas`, which
already copied all of the template's decorative shapes (colored rectangles, logo, bars).

Those decorative shapes were designed for the template's original (often light) background.
Now they sit on a dark background they were never intended for.

`_set_slide_background` only sets `slide.background.fill` — it does NOT remove the
cloned decorative shapes. They remain on the slide.

**Do not attempt**: trying to selectively remove "light-mode" shapes from a dark
section divider. This requires knowing which shapes are "decorative for light" vs.
"neutral" — not computable without LLM analysis of the template.

---

### [DEAD END — DO NOT REVISIT] Bug D: `_find_blank_layout` heuristic is misleading

**File**: [powergen/dynamic_renderer.py](powergen/dynamic_renderer.py) line 107

**What happens**:
Picks the layout with the fewest content placeholders and no explicit `<p:bg>` override,
intending this to be the "cleanest" canvas. But a layout with no `<p:bg>` override
*inherits* from the slide master, which may have its own visual decorations, background
fills, and fixed-position shapes.

"No explicit background override" does not mean "blank canvas" — it means
"inherits master background", which could be anything.

**Do not attempt**: improving the heuristic (e.g. counting shapes on the layout).
The information needed is: which slide master / layout produces a predictable,
decoration-free canvas for our dynamically placed textboxes. This is not derivable
from the PPTX structure alone without LLM interpretation.

---

### Architectural root cause (summary)

The `generate` command assumes that "template visual identity" = a set of tokens
(colors, fonts) + a set of copyable decorative shapes. This is wrong.

Template visual identity is a **spatial system**:
- Which zone is the title zone
- Which zone is the content zone
- Where decorations live and what area they consume
- How much space is left for content

None of these are captured in the current approach. Until the catalog phase can output
a `content_zone` per slide type (Option E in POWERGEN_ROADMAP.md), the `generate`
command cannot produce correct output regardless of content quality.

---

### Open decisions (carry forward, not resolved this session)

1. **content_zone extraction approach**: Option E (extend catalog to emit
   `{title_zone, body_zone}` via LLM vision call) is the recommended path, but not
   yet designed. Do not implement `generate` rendering changes until this is designed.

2. **generate command status**: Currently committed to the branch but produces incorrect
   output for any template with non-trivial decorative layout. Safe for demo of content
   generation quality only (use `--plan-only` to show without rendering).

---

## Session 2026-04-14 (continued) — Layer 2 completion

### What was implemented

**Layer 2 = `powergen fill` pipeline (catalog-driven, template-bound)**

The fill pipeline now has three phases:
1. `powergen catalog` → v3 catalog JSON with special_slides + reusable patterns
2. `powergen fill --plan-only` → op-based plan (fill_special / keep / clone_pattern)
3. `powergen fill` → fills template in-place and reorders/prunes slides

### Files changed

- **`powergen/prompts_catalog.py`** — rewritten for v3 (3-role classification: special/reusable/keep)
- **`powergen/catalog.py`** — added `_collect_valid_shape_names` + `_validate_catalog_slots` (shape hallucination fix), `extract_catalog` → v3 schema, `load_catalog_for_planner`
- **`powergen/prompts_catalog_planner.py`** — rewritten for fill_special/keep/clone_pattern ops
- **`powergen/catalog_planner.py`** — updated to use `load_catalog_for_planner`
- **`powergen/catalog_filler.py`** — full rewrite: `_copy_slide_rels`, `_clone_slide_full`, new `fill_from_plan`
- **`powergen/mock_client.py`** — added `_MOCK_CATALOG_V3_JSON`, `_MOCK_PLAN_V3_JSON`, updated detection
- **`powergen/cli.py`** — added `--template` flag to `fill` command for explicit template selection

### Verified

- Mock path (zero tokens): catalog → plan → fill works end-to-end, 7 slides
- Real API catalog: v3.0, no dropped slots, correct shape names, profile at source_slide=2
- Real API fill: 20-26 slides generated (LLM sampling variation), structurally valid PPTX
- Text eval via Claude Haiku: 5/10 overall (content 6, structure 5, template usage 4)

### Key design decisions

- **Duplicate shape names** (`TextBox 15` ×2 on slide 1): handled in `_fill_slide` by fill_count tracking, fills in encounter order
- **Shape validation**: after LLM catalog generation, all slot shape_names are cross-checked against programmatic extraction — invalid names dropped with warning
- **v2 catalog compat**: `load_catalog_for_planner` prints warning and returns empty patterns for v2 catalogs; `load_catalog_summary` unchanged for backward compat
- **Slide cloning**: `_clone_slide_full` copies ALL shapes (not strip+blank), preserves background, remaps r:embed/r:link/r:id for images

### Known limitations of Layer 2

1. **Planner over-generates** (20-26 slides for a simple brief) — planner prompt rule "max 3 consecutive same pattern" is followed but slide count is not capped
2. **Placeholder text** — planner generates `[Student Name]` etc. when brief doesn't specify names; acceptable behavior
3. **`keep` op not used in real API** — catalog classified all test.pptx slides as special or reusable, so no "keep" ops appear; mock path still tests keep
4. **No visual eval** — LibreOffice not available; eval done via text content comparison only

### Next session entry point

For Layer 2:
- Tune planner prompt to target 8-12 slides for typical briefs (currently 20-26)
- The output is **functionally correct** — template patterns correctly cloned and filled
- Real eval would need LibreOffice → PNG → vision scoring

For overall roadmap:
- Layer 2's `fill` command is working. `generate` command remains broken (bugs A-D above).
- **Do not touch `dynamic_renderer.py`** without content_zone design.
- Next big step is `content_zone` extraction (Option E in POWERGEN_ROADMAP.md)
