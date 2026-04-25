# Powergen Architecture

## 三层并行出口

v1 的假设（Layer 1→2→3 串行升级）已修正。三层是按场景选择的并行出口：

| Layer | 场景 | 输入 | 产出 | 智能在哪 |
|-------|------|------|------|----------|
| 1 — Scaffold | 没有模板，快速出骨架 | topic | 骨架 .pptx | LLM 做内容规划 |
| 2 — Template Fill | 有模板，要品牌一致的初稿 | .pptx 模板 + topic | 填充后的 .pptx（~70% 完成度） | LLM 做 slide 选择 + 文案 + shape 映射 |
| 3 — Full Visual | 要成品，愿意迭代 | topic（或 Layer 2 产出） | 演示级 .pptx | LLM 做视觉决策，人在 checkpoint 把关 |

---

## Layer 1 — Scaffold

两次 LLM 调用：plan 生成 → spec 生成 → 纯代码渲染（`renderer.py`）。
状态机：`INIT → PLANNED → APPROVED → RENDERED`（`state.py` 管理，持久化到 `.powergen/project.json`）。

---

## Layer 2 v2 — Clone + Best-effort Fill

### 为什么放弃 v1（Schema-Based）

v1 让人类替 LLM 做所有语义分析，把结论以封闭 JSON schema（slot_key、kind、reuse_tier、locator）预注入。
这固化了模型的思维路径，同时把配置成本（560 行 SKILL.md，2–4 小时 per 模板）转移给人。
详见 `archive/layer2_v1_schema` 的 `powergen/layer2/README.md`。

### 设计原则

> 用代码做信息密度压缩（去掉 XML 噪音，只留 shape name + 文本），
> 让 LLM 在语义上自由推断，不用人类预设的封闭类目约束。

### 流程

```
[1] inventory_gen.py（纯代码，零 token）
    → 遍历每张 slide，提取 layout name + 所有有文字的 shape（name + text preview）
    → 输出 slide_inventory JSON

[2] Composer LLM（单次调用）
    输入：slide_inventory + topic
    输出：
    {
      "slides": [
        {
          "source_slide_index": 0,
          "reason": "cover slide",
          "text_map": {
            "Title 2": "McMaster University — Math Program",
            "TextBox 15": "路觅学生：张伟"
          }
        },
        {
          "source_slide_index": 3,
          "clone_again": true,
          "reason": "reuse layout for second point",
          "text_map": { ... }
        },
        {
          "type": "generated",
          "content_type": "bullet",
          "fill": { ... }
        }
      ]
    }

[3] Clone + best-effort fill（纯代码）
    for each plan entry:
        clone source_slide → dest_prs
        for shape_name, new_text in text_map:
            shapes = [s for s in slide.shapes if s.name == shape_name]
            if shapes: replace_text(shapes[0], new_text)
            else: log warning, skip
        # generated entries → call renderer
```

### slide_inventory 格式

```json
{
  "slides": [
    {
      "index": 0,
      "layout": "封面",
      "shapes": [
        {"name": "Title 2", "text": "麦克马斯特大学 数学专业"},
        {"name": "TextBox 15", "text": "路觅学生：[ — ]"},
        {"name": "TextBox 15", "text": "路觅导师：[ — ]"}
      ]
    }
  ]
}
```

- 不做任何分类（reusable/generated/skip）
- 保留重名 shape（LLM 靠原始文本区分用途）
- 不含坐标/尺寸（对 LLM 文案决策无用）

### Renderers（fallback）

保留 `renderers/` 作为 fallback。当 LLM 判断模板里没有合适的 slide 时，可以输出 `type: generated`，走现有 renderer（bullet / card / flow 等）。

---

## Layer 3 — Compositional Deck Generation

### 核心定位

> **无模板，从零生成结构正确、可读的完整 deck。**

Layer 1 填模板，Layer 2 选模板，Layer 3 组合组件。
不追求设计感，追求"结构正确 + 组合合理"。

---

### 状态机

```
CONTENT_PLAN ──approve──→ SLIDE_GEN ──→ QA ──→ OUTPUT
```

- **DESIGN_SPEC 已删除**：视觉风格作为隐式 style context 注入 SLIDE_GEN，不单独作为阶段
- **无 per-slide loop**：一次性生成完整 deck，用户看整体结果后决定 approve / 全局 redo
- **QA 检查组合合理性**，不只检 overflow

### Checkpoint 说明

**CONTENT_PLAN**：LLM 输出 slide 列表（index, purpose, key_message）。纯内容，不涉及视觉。用户 approve / edit。

**SLIDE_GEN**：LLM 读 slide 列表 + style context → 输出 compositional spec → 纯代码渲染。一次性生成完整 deck，不逐张 loop。

**QA**：LLM 检查组合合理性，输出问题列表（不自动修）。用户决定是否 redo SLIDE_GEN。

---

### Compositional Spec 格式

> **Layer 3 的核心：spec 从线性结构升级为组合系统。**

```json
{
  "slides": [
    {
      "layout": "two_column",
      "title": "Why PowerGen",
      "style": {"accent": "#2563EB"},
      "blocks": [
        {"type": "bullet_group", "region": "left", "items": ["Manual PPT is slow", "Templates are rigid"]},
        {"type": "stat", "region": "right", "value": "87%", "label": "效率提升"}
      ]
    }
  ]
}
```

**4 个 layout（固定，不爆炸）：**

| layout | regions |
|--------|---------|
| `title_slide` | center |
| `single_column` | main |
| `two_column` | left / right |
| `comparison` | left / right（带标题栏） |

**5 个 block type（初始）：**

| block | 说明 |
|-------|------|
| `bullet_group` | 列表 |
| `stat` | 大数字 + 标签 |
| `quote` | 引用块 |
| `note` | 小字注释 |
| `heading` | 段落标题 |

**Layer 1 vs Layer 3 spec 对比：**

```
Layer 1（线性）：{layout, title, bullets}
Layer 3（组合）：{layout, title, style, blocks: [{type, region, ...}]}
```

---

### Renderer 架构（解耦，Phase 1 / Phase 2 共用 spec）

```
powergen/layer3/
  composer.py       # 状态机
  planner.py        # LLM: topic → slide list
  spec_builder.py   # LLM: slide list + style ctx → compositional spec
  renderer.py       # 抽象层（接口）
  renderers/
    pptx.py         # Phase 1：python-pptx 实现
    browser.py      # Phase 2：Playwright → bbox → PPTX
  layouts/          # 4 个 layout 定义（region 坐标 / HTML template）
  blocks/           # 5 个 block renderer
  qa.py             # 检查组合合理性
```

**Renderer 解耦原则**：spec 格式固定，Phase 1 用 `PptxRenderer`，Phase 2 加 `BrowserRenderer`，状态机和 spec 不变。

---

### Phase 2：HTML / Playwright 渲染后端

```
DSL (compositional spec)
  → HTML template fill（受限 HTML，class 是语义不是样式）
  → Playwright headless（fixed viewport = 1280×720 = slide size）
  → getBoundingClientRect() → EMU 坐标
  → python-pptx shapes（按 bbox 定位）
```

**必须约束（否则不可控）：**
- HTML 是 DSL，不是自由网页（固定 class 白名单）
- CSS 只用 layout subset（flex/grid/padding/color，禁 position:absolute / transform）
- viewport 固定，字体锁定（防 layout drift）
- PPTX 是近似渲染，不追求 fidelity 完全复现

**QA 规则（Phase 1 基础版）：**
- `stat` + 长文本同 region → 警告
- `bullet_group` items > 6 → 建议拆 slide
- region 内 block 超过 2 个 → 警告密度过高

---

### Style Context（隐式，非阶段）

- 有模板 → 从 Layer 2 inventory 提取主色 + 字体
- 无模板 → hardcode 2–3 套 default theme
- 用户可通过 `--theme` 选择，不作为独立 checkpoint