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
