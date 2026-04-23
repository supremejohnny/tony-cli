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
- Schema v2: TABLE/GROUP support, layout metadata, visual_only, decorative_heavy — done
- LLM Annotator (annotator.py, --annotate flag) — done
- normAutofit font overflow fix — done
- Prompt polish (quoted keys + CRITICAL RULES, slot_label/confidence) — done
- fill skip-if-not-in-fill (preserve clone content for unfilled slots) — done
- API test with annotated schema — done (stylish1 replacement confirmed)

## Layer 2.5 — Schema-Driven Style Inference  `planned`

**Concept**: Template is reference only for visual style; model generates content-appropriate
slide layouts by mimicking the template's aesthetic rather than cloning its exact structure.

**Motivation**: A 5-slide template can't cover all needed slide types. The schema already has
layout metadata (top_pct, left_pct, width_pct, height_pct, font_size_pt, font_name) and
design tokens (colors, fonts from slide master). This is enough for the model to generate
new slides that visually match the template without needing a source slide to clone.

**Target slide types** (each a simple renderer + style token injection):
- `subtitle_text`: section divider — large subtitle + single text box
- `two_column`: left/right equal columns with heading + body
- `grid_2x2` / `grid_3x1`: evenly spaced cards mimicking template card layout
- `title_bullets`: standard title + bullet list matching template body font/size

**Implementation sketch**:
- `style_extractor.py` — derive design tokens from schema: dominant font, heading size, body size, accent color, background color
- Each renderer accepts `style_tokens` dict and applies them (font name, size, color) instead of hardcoded values
- Composer LLM can select these generated slide types in the plan when no reusable slide fits

**Not started** — requires design token extraction from pptx slide master/theme XML.

## Layer 3 — Full Visual  `not started`
- Node.js / pptxgenjs toolchain setup — not started
- Design spec + code generation pipeline — not started
- QA loop (soffice → image → inspect) — not started

---

**Next**: Layer 1 prompt iteration OR Layer 2.5 style inference (TBD).
