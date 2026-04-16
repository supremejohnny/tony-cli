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
