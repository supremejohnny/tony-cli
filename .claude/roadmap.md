# Powergen Roadmap

## Layer 1 — Scaffold  `in progress`
- Core pipeline (plan → spec → render, state machine) — in progress ~70%
- Prompt iteration on real API responses — not started
- Render diversity (comparison, section divider, stats callout) — not started

## Layer 2 — Schema-Based Template Composition  `in progress`
- Schema spec + validator (SKILL.md, test_template.schema.json, validate.py) — done
- Composer core (schema_loader, slot_resolver, slide_cloner, renderers) — done
- Auto-schema generation (schema_gen.py, nth deduplication) — done
- CLI integration (powergen template --pptx) — done
- Font/formatting polish (theme fonts, PLACEHOLDER slot fill) — not started

## Layer 3 — Full Visual  `not started`
- Node.js / pptxgenjs toolchain setup — not started
- Design spec + code generation pipeline — not started
- QA loop (soffice → image → inspect) — not started

---

**Next**: Layer 2 formatting polish → Layer 1 prompt iteration.
