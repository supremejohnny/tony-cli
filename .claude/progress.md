# Claude Progress Log

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

**Files modified**:
- `powergen/layer2/composer/schema_gen.py` — Two-pass name counting: if a shape name appears more than once, ALL occurrences get `nth` (including nth=0), preventing ambiguous slot lookups

---

## 2026-04-23 — Session 5

**Branch**: `dev/powergen_layer2_ver1`

**Topics**: Semantic Inference Pipeline — schema v2 + LLM annotator + TABLE/GROUP support + normAutofit

**Problem analyzed in Session 4.5 (design session)**:
- `schema_gen` blind to TABLE shapes (has_text_frame=False) → tables in template never replaced
- `schema_gen` blind to GROUP sub-shapes → shapes inside groups ignored
- Decorative font encoding (Wingdings, custom dingbat fonts) → garbled defaults → LLM can't infer slot semantics
- Generic shape names ("object 4", "object 5") → LLM generates wrong fill keys → zero replacement
- Font overflow: no normAutofit in bodyPr → large-font shapes clip text on replacement

**Implementation: Semantic Inference Pipeline (P1–P5)**

**Files modified**:
- `powergen/layer2/composer/schema_gen.py` — Schema v2: GROUP sub-shapes flattened via `_iter_shapes()`, TABLE shapes extracted as kind="table" (2D list default), layout metadata per slot (top_pct/left_pct/width_pct/height_pct/font_size_pt/font_name), `visual_only` flag (decorative font detection: known Wingdings-family OR Latin Extended U+0100-U+024F ratio >15%), slide-level `decorative_heavy` flag (n_shapes>10 and avg_chars<12 OR n_shapes>6 and short_ratio>0.7 where "short"=word_count≤3 AND char_count≤8 — avoids Chinese text false positives); `load_or_generate` regenerates if schema_version < "2"
- `powergen/layer2/composer/slot_resolver.py` — `_all_shapes()` + `_iter_group()` recursively search GROUP containers, `resolve()` and `resolve_repeating_field()` now use `_all_shapes()` instead of `slide.shapes`
- `powergen/layer2/composer/slide_cloner.py` — TABLE kind handling in `_fill_slots()` (calls `_set_table()` → `_set_table_cell()`); `_ensure_norm_autofit()` applied after every `_set_text()` / `_set_multiline()` (replaces `noAutofit` with `normAutofit`, or adds if absent — prevents text overflow without breaking shapes that already have normAutofit/spAutoFit)
- `powergen/layer2/composer/annotator.py` — NEW: LLM annotator reads v2 schema, outputs slide-level composable flag + slot-level semantic label (title/subtitle/body/label/caption/callout) + confidence (high/medium/low); post-processing enforces role whitelist, uniqueness (max 1 title/subtitle per slide), high-confidence count cap (≤3/slide); caches as `<stem>.annotated.json`
- `powergen/layer2/composer/planner.py` — `_build_prompt()` now surfaces `slot_label` + `confidence` from annotations in slot descriptions; non-composable/decorative_heavy slides shown with `[NON-COMPOSABLE]` / `[decorative-heavy]` suffix and no slot expansion; TABLE slots shown with `{rows}×{cols} table — value must be list of lists`
- `powergen/cli.py` — `--annotate` flag runs annotator and exits; on normal runs, loads `.annotated.json` if present and merges into schema (prints diagnostic count of non-composable/decorative slides)

**Key design decisions**:
- "short" shape uses char_count ≤ 8 threshold (not word_count alone) to avoid false positives on Chinese text sentences without spaces
- annotator is opt-in (manual `--annotate` run), not auto-invoked, to avoid silent API calls
- normAutofit: only replaces noAutofit or absent autofit — leaves spAutoFit alone

**Test result**: both `courseplan_test.pptx` and `stylish1_test.pptx` pass mock end-to-end. `courseplan_test.schema.json` upgraded to v2 with 1 TABLE slot on slide_8.

---

## 2026-04-23 — Session 5 (continued): debug zero-replacement on stylish1

**Symptoms**: `layer2_api_stylish1_test2_haiku.pptx` and `test3` had no text changes vs template.

**Root cause analysis** (three compounding bugs):

**Bug 1 — LLM generates semantic fill keys instead of exact schema keys**
- Old prompt: `Slots: object 2 (text, was: 'PROPOS6Į'), ...` — LLM read this as description, generated `{"title": "PROPOSAL"}` instead of `{"object 2": "PROPOSAL"}`
- `fill.get("object 2")` → None → fell through to default ("PROPOS6Į") → clone unchanged
- Fix: restructured prompt so each slot is a quoted key on its own line: `"object 2": text | was: "PROPOS6Į"`, plus CRITICAL RULES block with WRONG/RIGHT examples

**Bug 2 — annotator over-classified all slides as non-composable**
- Old system prompt: "false if text is unreadable (garbled font encoding)"
- LLM saw garbled defaults (PROPOS6Į etc.) and marked all 5 slides `composable: false` → Composer LLM told to use `fill: {}` for all → zero replacement
- Fix: system prompt now says composable: false ONLY for `decorative_heavy=true`; `_post_process` adds hard override restoring composable: true for any slide not tagged decorative_heavy in schema
- Deleted stale `stylish1_test.annotated.json`

**Bug 3 — fill fallback to truncated default overwrites clone content**
- When `fill` dict is `{}` or key missing: `value = fill.get(slot_key) → None → value = slot_def.get("default")` → wrote 120-char truncated version back into shape (overwriting full original text from clone)
- Fix: `_fill_slots` now uses `if slot_key in fill` check — missing key → skip entirely, keeping clone's original text untouched

**Key insight about stylish1's "garbled" text**: The Latin Extended chars (Į, ľ, etc.) are not font glyph-map encoding — they ARE the actual characters the template creator typed for visual effect. Writing normal ASCII into those shapes renders normally with the same decorative font style. So stylish1 IS composable; it was just being blocked by the bugs above.

**Files modified in this debug pass**:
- `powergen/layer2/composer/planner.py` — quoted-key prompt format + CRITICAL RULES block
- `powergen/layer2/composer/annotator.py` — system prompt + `_post_process` composable override
- `powergen/layer2/composer/slide_cloner.py` — `_fill_slots` skip-if-not-in-fill logic

**Test result**: API test with stylish1 confirmed successful content replacement after fixes.
