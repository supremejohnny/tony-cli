# Claude Progress Log

Concise per-session record of what was discussed and decided.

---

## 2026-04-15 — Session 1

**Branch**: `dev/powergen_layer2_ver1`

**Topics**: Layer 2 architecture review; codebase reorganization

**Key decisions**:
- Markitdown-based Layer 2 (`template_filler.py`) is a dead end. Root cause: flat text extraction with no shape identity — can't handle duplicate shape names, repeating groups, or decoration vs slot distinction.
- New direction: schema-based composition (three actors — Composer LLM / Composer code / Renderers). LLM operates on a small enumerable decision space, not on open-ended visual design.
- `test_template.schema.json` (worked example for `test.pptx`) and `SKILL.md` (schema authoring methodology) are the foundation of Layer 2.

**Files deleted**:
- `powergen/template_filler.py` — markitdown approach
- `powergen/prompts_template.py` — tied to above
- `test/.powergen_catalog/` — catalog v3.0 attempt (earlier dead end)
- `.powergen_distill/` — distill experiment residue
- `.powergen/project.json` — stale runtime state

**Files created / moved**:
- `powergen/layer2/__init__.py` — Layer 2 subpackage
- `powergen/layer2/SKILL.md` — moved from repo root
- `powergen/layer2/schemas/test_template.schema.json` — moved from repo root
- `powergen/layer2/scripts/validate.py` — schema validator (was at root, identified and moved)
- `layer3/.gitkeep` — Layer 3 placeholder
- `powergen/README.md` — directory structure + run commands
- `POWERGEN_ROADMAP.md` — updated: old Layer 2 struck through, new Layer 2 roadmap added

**Files modified**:
- `powergen/cli.py` — removed `template` subcommand (broken after deletion); left TODO comment for Layer 2 re-implementation

**Layer 2 status after this session**:
- Schema spec: done (`SKILL.md` + `test_template.schema.json`)
- Schema validator: done (`layer2/scripts/validate.py`)
- Composer: not started (next: `inspect_pptx.py` → `schema_loader` → `slot_resolver` → `slide_cloner` → renderers)

---

## 2026-04-16 — Session 2

**Branch**: `dev/powergen_layer2_ver1`

**Topics**: Layer 2 composer full implementation; auto-schema generation; first real API test

**Key decisions**:
- Hand-authored schema per template is not scalable → add local auto-schema generation (`schema_gen.py`) that extracts shape structure from any pptx without LLM. Schema cached as `<pptx>.schema.json` alongside the source file.
- `powergen template --pptx <file>` replaces `--schema` as the primary entry point; `--schema` kept for advanced/hand-authored override.
- Composer LLM prompt now includes each slot's original text as `was: '...'` so the model can infer purpose without reading a hand-authored description.

**Files created**:
- `powergen/layer2/composer/schema_loader.py` — load + strip `_comment*` fields from schema JSON
- `powergen/layer2/composer/slot_resolver.py` — resolve `shape_name` / `nth` / `near` locators to shapes
- `powergen/layer2/composer/slide_cloner.py` — clone reusable slide (lxml deep-copy + OPC part transfer) + fill all slot kinds
- `powergen/layer2/composer/composer.py` — orchestrate reusable clone + generated renderer calls
- `powergen/layer2/composer/planner.py` — Composer LLM call + `mock_plan()`
- `powergen/layer2/composer/renderers/__init__.py`, `_common.py`, `card.py`, `bullet.py`, `flow.py`
- `powergen/layer2/composer/schema_gen.py` — **local** pptx → schema extraction (no LLM)
- `powergen/layer2/scripts/inspect_pptx.py` — shape inventory dump
- `powergen/layer2/scripts/test_cloner.py` — eval script for slide_cloner

**Files modified**:
- `powergen/cli.py` — `template` subcommand re-implemented; `--pptx` (auto-schema) + `--schema` (manual) as mutually exclusive args
- `powergen/mock_client.py` — Layer 2 composer dispatch added
- `powergen/layer2/composer/planner.py` — prompt updated to show slot defaults
- `powergen/layer2/schemas/test_template.schema.json` — `source_pptx` path corrected to `../../../test/test.pptx`

**First real API test result** (Haiku, MBTI topic on `test/test.pptx`):
- Pipeline runs end-to-end; 15-slide plan generated correctly
- Content IS being placed in most slides
- **Known issue 1 — Slot fill failures on some slides**: a few reusable slides show original template text instead of generated content. Likely cause: PLACEHOLDER-type shapes have a different name resolution path vs TEXT_BOX shapes.
- **Known issue 2 — Font / formatting degradation**: filled text sometimes loses the template font (falls back to system default) and bullet formatting looks off. Root cause: `_set_text` preserves `<a:rPr>` but theme font references (`<a:latin typeface="+mj-lt">`) may not resolve correctly in the cloned slide without its original slide layout relationship.

**Layer 2 status after this session**:
- Composer: **fully implemented** (all modules done)
- Auto-schema: **done** (local extraction, no LLM)
- CLI integration: **done** (`powergen template --pptx <file> --topic "..."`)
- Remaining: font/formatting fix; slot fill reliability on PLACEHOLDER shapes

---

## 2026-04-18 — Session 3

**Branch**: `dev/powergen_layer2_ver1`

**Topics**: Visual fix — layout-inherited decorative shapes lost during slide clone

**Root cause identified**:
- `compose()` used `Presentation()` (fresh default template) → wrong theme/master/layouts
- `_clone_slide()` used `blank_layout(dest_prs)` → cloned slides used wrong layout
- Result: layout-level decorative shapes (e.g., `矩形 7` dark overlay panel in `议程` layout) were invisible on cloned slides; text rendered with default black theme instead of template theme colors

**Key findings from inspection**:
- ALL shapes in test.pptx are PLACEHOLDER shapes (no text boxes at all)
- Decorative shapes like dark overlay panels live in SLIDE LAYOUTS, not in slides' own spTree
- Auto-schema (`schema_gen.py`) generates correct shape names; hand-authored `test_template.schema.json` has wrong shape names (different pptx version)
- `_next_slide_partname` in python-pptx uses `len(sldIdLst) + 1`; clearing sldIdLst without dropping rels causes duplicate names in ZIP

**Files modified**:
- `powergen/layer2/composer/composer.py` — `compose()` now initializes dest_prs from BytesIO copy of src_prs (preserving master/layouts/theme); `_clear_slides()` drops both sldId XML elements AND slide relationships to prevent ZIP duplicate name warnings
- `powergen/layer2/composer/slide_cloner.py` — Added `_find_layout()` (match by layout name); `_clone_slide()` now uses matching layout from dest_prs instead of blank_layout

**Result**: Cloned slides now inherit correct layout → dark overlay panel visible, theme colors correct, PLACEHOLDER slot filling works. No ZIP warnings.

---

## 2026-04-18 — Session 4

**Branch**: `dev/powergen_layer2_ver1`

**Topics**: API test with real template (`courseplan_test.pptx`); ambiguous shape fix

**API test result** (Haiku, topic "麦克马斯特大学数学专业 course plan", `courseplan_test.pptx`):
- Pipeline runs end-to-end, 11-slide plan composed correctly ✅
- Style and fonts preserved successfully ✅
- Minor line-spacing deviations (likely template-level, acceptable)
- **Remaining issue**: 4 slots skipped with "Ambiguous: 2 shapes named X" warning
  - Affected: `TextBox 15`, `标题 7`, `文本占位符 9`, `文本占位符 12`
  - Root cause: `schema_gen.py` generates the first occurrence of a duplicated name WITHOUT `nth`, but slot_resolver requires `nth` when name is ambiguous

**Files modified this session**:
- `powergen/layer2/composer/schema_gen.py` — Two-pass name counting: if a shape name appears more than once, ALL occurrences get `nth` (including nth=0), preventing ambiguous slot lookups
