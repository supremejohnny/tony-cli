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

## Layer 3 — Conversation Loop with Checkpoints

### 状态机

```
[1] CONTENT_PLAN ──approve──→ [2] DESIGN_SPEC ──approve──→ [3] SLIDE_GEN
                                                                  │ per-slide loop
                                                                  ▼
                                                           [4] QA_REVIEW
                                                                  ▼
                                                           [5] OUTPUT
```

每个 checkpoint：用户可 approve / 修改 / 重做当前阶段。

### Checkpoint 说明

**[1] CONTENT_PLAN**：LLM 输出 slide 结构（purpose + key_message）。纯内容，不涉及视觉。

**[2] DESIGN_SPEC**：LLM 输出 palette + font_pair + per-slide layout 方向。
若提供 .pptx 模板，从模板自动提取 palette/font 作为默认值。

**[3] SLIDE_GEN**：逐张生成 → soffice 渲染预览 → 用户 approve/redo。
前序 slide 的修改结果成为后续 slide 的 context（风格一致性）。

**[4] QA_REVIEW**：LLM 自检全部 slide（字体一致性、对齐、文字溢出）→ 输出问题列表 → 用户确认修复范围。

### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| Slide 生成 | python-pptx（先）| 和现有代码库一致，先跑通流程 |
| 预览渲染 | libreoffice --headless → pdf → pdftoppm → png | 免费，CI 友好 |
| 模型 | Sonnet | 视觉决策需要更强的推理能力 |
| 交互界面 | CLI REPL（先）→ Web UI（后） | 先验证 loop 设计 |

### Layer 2 → Layer 3 衔接

```bash
powergen visual --from-template my_template.pptx --topic "..."
```

Layer 2 的 inventory 为 Layer 3 的 CONTENT_PLAN 提供模板结构感知；
Layer 2 的 inventory 为 DESIGN_SPEC 提供默认 palette/font。
Layer 3 不依赖 Layer 2，没有模板也能独立运行。
