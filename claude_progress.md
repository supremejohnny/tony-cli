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
