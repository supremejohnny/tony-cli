# Progress Archive

Compressed session records. Only persistent decisions and final state — process omitted.

---

## 2026-04-15 — Session 1 (compressed)

**Branch**: `dev/powergen_layer2_ver1`

**Decision**: Abandoned markitdown Layer 2 (`template_filler.py`, `prompts_template.py` deleted). Root cause: flat text, no shape identity. Pivoted to schema-based composition (three actors: Composer LLM / Composer code / Renderers).

**Foundation**: `SKILL.md` (schema authoring) + `test_template.schema.json` (example) + `validate.py` (validator) created. Composer not started at end of session.

**Cleanup**: `template_filler.py`, `prompts_template.py`, `test/.powergen_catalog/`, `.powergen_distill/`, `.powergen/project.json` deleted.

---

## 2026-04-16 — Session 2 (compressed)

**Branch**: `dev/powergen_layer2_ver1`

**Decision**: Hand-authored schema not scalable → added `schema_gen.py` (local auto-schema extraction, no LLM, cached as `<pptx>.schema.json`).

**Decision**: `powergen template --pptx <file>` as primary entry; `--schema` kept for manual override. Composer LLM prompt includes `was: '...'` per slot so model infers purpose from defaults.

**Completed**: All composer modules — schema_loader, slot_resolver, slide_cloner, composer, planner, renderers (card, bullet, flow), inspect_pptx.py. Pipeline end-to-end working.

**Known issues at end of session**: Slot fill failures on PLACEHOLDER shapes; font/formatting degradation (theme font refs in cloned slides not resolving). → Both addressed in Session 3.
