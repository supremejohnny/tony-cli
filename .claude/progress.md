# Claude Progress Log

---

## 2026-04-23 — Session 9

**Branch**: `dev/powergen_layer2_ver1`

**Topics**: Sonnet JSON 修复 + API 测试验证（courseplan_test.pptx）

**状态**: ✅ 成功 — pipeline 端到端运行，内容替换正常，视觉质量中等

**修复内容**:
- `spec.py` + `annotator.py`: `_parse_json` 加多阶段 fallback（直接解析 → 提取 `{}` block → strip trailing commas）
- 解决 Sonnet 返回带语法错误 JSON 时崩溃的问题

**API 测试结果（courseplan + Haiku/Sonnet）**:
- Haiku: 13 slides (9 reusable, 4 generated) — 效果不错
- Sonnet: 15 slides (10 reusable, 5 generated) — JSON 修复后正常

**遗留问题（已知，优先级待定）**:

1. **Section 编号错误** — subsection slide 显示 "04." 而非 "01."（第一个 section）。根因：subsection slide 内有数字 placeholder，compiler 填充时没有做序号注入，LLM 生成的 spec 也没有序号字段，导致模版原始数字（04）保留不变
2. **品牌 logo 缺失** — generated slides（card_grid 等）没有模版的 LUMIST logo 装饰。根因：logo 是 layout-level 图片，只有 reusable slides（继承 layout）才有；generated slides 用 blank_layout，无法自动继承
3. **Table 内容未替换** ✅ 已修复（Session 9）— 根因：annotator 给 table slot 打了 slot_label="body"，_get_label_map 把它当文本 slot 处理，compiler 写入字符串，slide_cloner 因 not isinstance(str, list) 跳过。修复：_get_label_map 排除 kind="table" slot；_fill_reusable 新增 table 专属填充路径（items/steps/cards → 2D list）。
4. **Annotator 需精进 — table slot 不应打 label** — 当前 annotator 给 table slot 打 slot_label="body" 是语义合理但架构上错误的（compiler 专门处理 table，annotator label 在这里被忽略）。未来应在 annotator system prompt 中明确规定：table slot 跳过 label 标注（类似 visual_only 的处理）。待 --annotate 重新运行后验证。

---

## 2026-04-23 — Session 8

**Branch**: `dev/powergen_layer2_ver1`

**Topics**: 补漏 annotator intent_tags + 品牌色修复

**CLAUDE.md 新增规则**: 跨 session 继续实现任务时，编码前必须从 progress.md 还原完整待办步骤列表，逐条确认，不得跳过或静默合并步骤

**补漏 — annotator intent_tags（原待办步骤 5）**:
- `annotator.py` 升至 v2: `_ANNOTATOR_VERSION = "2"`, `_INTENT_WHITELIST`（8 个 intent）
- system prompt 新增 intent_tags 输出指令：区分 section vs list（关键：body slot 的 h= 高度），max 2 tags，闭集合限定
- `_build_prompt` 新增: 显示 schema_gen 推断的 intent_tags 作为 hint；在位置信息里加 `h=height_pct`（让 LLM 能判断 body area 大小）
- `_post_process` 新增: intent_tags 白名单验证，截断到 max 2
- `merge_into_schema` 新增: annotator 的 intent_tags 覆盖 schema_gen 的推断（annotator 有更多视觉上下文）
- `load_or_annotate`: 缓存版本 < "2" 时重新生成
- `cli.py`: 加载注解时检查版本，打印升级提示

**品牌色修复**:
- `schema_gen.py`: 新增 `_SCHEME_ACCENT_INDEX` 和 `_find_brand_accent_index(prs, n_accents)` —— 扫描所有 slide XML 的 `a:schemeClr val="accent*"` 引用，找最高频率的 accent 作为品牌色；结果存入 `tokens["brand_accent_index"]`
- `renderers/_common.py`: 新增 `brand_accent(tokens, offset=0)` = `accent(tokens, brand_accent_index + offset)`
- 所有 renderer 从 `accent(tokens, 0/i)` 改为 `brand_accent(tokens, 0/i)`: section_divider, bullet, two_column, card_grid, flow

**局限性说明**: courseplan 的可见橙色（logo）以 srgbClr 存储，不在 pptx scheme accent 体系内，无法自动识别为品牌色；brand_accent_index=0（蓝）是结构层面正确答案。stylish1 同理。对大多数标准模板（品牌色就是 accent 颜色）此机制有效。

**测试**: mock 两模板均通过；注解版本检查正常

---

## 2026-04-23 — Session 7

**Branch**: `dev/powergen_layer2_ver1`

**Topics**: Two-phase pipeline (Call 1 + Call 2) — replaces single-call planner

**Architecture change**:
- OLD: single LLM call (planner.py) saw template schema → generated plan.json directly; caused template-dominated output, generated slides always appended at end
- NEW: Call 1 (spec.py) — template-unaware, topic → spec IR (intent-tagged blocks); Call 2 (compiler.py) — deterministic, spec + schema → plan.json

**Files created**:
- `powergen/layer2/composer/spec.py` — Call 1: `generate_spec(topic, client)` + `mock_spec()`; 8-intent vocabulary: cover/section/list/comparison/process/group/highlight/closing; spec IR fields per intent (items/steps/pairs/cards/body)
- `powergen/layer2/composer/compiler.py` — Call 2: `compile_plan(spec, schema)` + helpers; intent_index from schema intent_tags; `_pick_reusable` uses least-used strategy; `_fill_reusable` uses slot_label (annotator) → inferred_label (schema_gen) fallback; `_fill_generated` normalizes per structure_type; subtitle→body fallback for content-heavy intents; `_put` writes to first matching slot only

**Files modified**:
- `powergen/layer2/composer/schema_gen.py` — v4: `_LAYOUT_INTENT_MAP` (Chinese+English layout name patterns), `_infer_intent_tags(layout_name)`, `_infer_slot_labels(slots)` (font size + position heuristic → title/subtitle/body); positional fallback (slide_0 → ["cover"], slide_N → ["closing"]); removed `reuse_tier` and `compose_hints` from output
- `powergen/layer2/composer/composer.py` — removed `content_type` fallback
- `powergen/layer2/composer/planner.py` — replaced with stub (raises ImportError)
- `powergen/cli.py` — `_run_template` rewired to spec + compiler; prints plan breakdown (N reusable, N generated)

**Key design decisions**:
- `_put` writes to first matching label slot (not all) — avoids flooding complex multi-box slides
- subtitle→body fallback: for list/process/highlight/comparison/group/closing intents, if no "body" slot but "subtitle" slot exists, use subtitle (annotator sometimes labels the content area as "subtitle")
- Positional intent inference: first slide → cover, last slide → closing (catches templates with blank/unnamed layouts)
- No LLM in compiler — strictly deterministic; annotator's slot_label used if cached, otherwise inferred_label

**Test result**: mock pipeline passes for both courseplan (9 slides: 4 reusable, 5 generated) and stylish1 (9 slides: 3 reusable, 6 generated). Slides correctly interleaved (not appended). Cover/closing from template, generated slides for comparison/process/cards.

---

## 2026-04-23 — Session 6

**Branch**: `dev/powergen_layer2_ver1`

**Topics**: Schema v3 + structure_type semantic layer + 3 new renderers

**Design decisions made**:
- `tokens: {}` was always empty in v2 — v3 fills it from pptx theme XML
- `generated_slides: {}` was always empty in v2 — v3 populates with 5 fixed renderer definitions
- LLM outputs `structure_type` (semantic vocabulary), code maps deterministically to renderer (no LLM free choice on visual layout)
- `structure_type` enum: `list / comparison / cards / process / section` (5 values, no overlap)
- Backward compat: `content_type` still works in composer via fallback chain

**Files modified**:
- `powergen/layer2/composer/schema_gen.py` — v3: `_get_theme_el()` (theme XML via blob), `_resolve_color()`, `_is_dark()`, `_extract_tokens()` (fonts from majorFont/minorFont, accent_colors, dk1_hex, lt1_hex, bg_is_dark, heading/body sizes from slot aggregation); `_GENERATED_SLIDES` constant; `generate()` now calls `_extract_tokens` and writes both `tokens` and `generated_slides`; `load_or_generate` regenerates on version < "3"
- `powergen/layer2/composer/renderers/_common.py` — updated `primary()` / `title_size()` / `body_size()` to support v3 flat token format (with v1 fallback); added `text_color()`, `heading_font_name()`, `body_font_name()`; added `font_name` param to `add_text()` / `add_text_multiline()`
- `powergen/layer2/composer/renderers/__init__.py` — registered `title_bullets` (alias to bullet), `two_column`, `card_grid`, `section_divider`
- `powergen/layer2/composer/composer.py` — added `STRUCTURE_TO_RENDERER` dict; generated slide routing now reads `structure_type` → maps to renderer name → calls renderer
- `powergen/layer2/composer/planner.py` — generated slides section now shows structure_type values + fill format examples; output format updated to `structure_type`; `mock_plan` exercises all 5 structure types

**New files**:
- `powergen/layer2/composer/renderers/section_divider.py` — accent bars top/bottom, large title + subtitle
- `powergen/layer2/composer/renderers/two_column.py` — two accent-header columns side by side
- `powergen/layer2/composer/renderers/card_grid.py` — 2×2 or 3×1 cards with left accent border

**Test result**: `mock_plan` end-to-end with courseplan_test.pptx passes — 5 slides (section/list/comparison/cards/process). Token extraction: courseplan accent_colors `["#4874CB","#EE822F","#F2BA02","#75BD42"]`; stylish1 accent_colors `["#4F81BD","#C0504D","#9BBB59","#8064A2"]`. bg_is_dark correctly false for both (light lt1).

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
