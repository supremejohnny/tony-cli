# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 沟通

- 使用中文沟通
- 回复简洁直接，没有指示的情况下不需要过度解释。交付功能的 chat 在最后简述做了什么，如何测试
- 发现更优路径后主动建议，不要单纯遵循 prompt

## 工作习惯

- 复杂的改动或功能先行讨论方案，简单的 debug 和 bug 修复直接做
- 修改超过 3 个文件时拆分成小任务
- 开始编码前先读 `.claude/roadmap.md` 和 `.claude/progress.md` 了解当前进度和决策背景
- 跨 session 继续实现任务时，编码前必须从 progress.md 还原完整的待办步骤列表，明确标出哪些已完成、哪些待做，再开始。不得跳过或静默合并步骤

## 编码

- 尽量减少注释，除非逻辑不明显
- 修改现有代码时保持原有风格

---

## Project Context

- `.claude/roadmap.md` — 里程碑进度，开始新功能前先看
- `.claude/progress.md` — 最近 2-3 个 session 的详细记录，每次 session 开始时看
- `.claude/progress_archive.md` — 历史 session 压缩归档，仅回溯决策时看
- `.claude/architecture.md` — 架构设计和决策理由，涉及架构变更时看

---

## 项目架构

**PowerGen** — AI 演示文稿生成器，三层并行出口架构，均位于 `powergen/` 下。

### Layer 1 — Scaffold（完成）

`powergen/{cli,planner,spec_builder,renderer,prompts,state,models,workspace,mock_client,repl}.py`

状态机流程：`INIT → PLANNED → APPROVED → RENDERED`（由 `state.py` 管理，持久化到 `.powergen/project.json`）。
两次 LLM 调用：plan 生成（`planner.py`）→ spec 生成（`spec_builder.py`）→ 纯代码渲染（`renderer.py`）。

### Layer 2 — Clone + Best-effort Fill（进行中）

`powergen/layer2/`

三步流程：
1. **`inventory_gen.py`**（纯代码）— 遍历模板每张 slide，提取 layout name + 所有有文字的 shape（name + text preview），输出轻量 `slide_inventory`，零 LLM token。
2. **Composer LLM**（单次调用）— 读 inventory + topic，输出 slide 选取计划（`source_slide_index` + `text_map`），直接用 shape_name 映射新文案。同一张 slide 可被多次选取（clone 多份）。
3. **Clone + fill**（纯代码）— 按计划 clone slide，best-effort name-match 填充文本，无精确 locator。Renderers 作为 fallback（模板无合适 slide 时 LLM 输出 `type: generated`）。

**设计原则**：用代码做信息密度压缩（去掉 XML 噪音，只留 shape name + 文本），让 LLM 在语义上自由推断，不用人类预设的封闭类目约束。

### Layer 3 — Full Visual（未开始）

状态机：`CONTENT_PLAN → DESIGN_SPEC → SLIDE_GEN → QA_REVIEW → OUTPUT`。
逐张生成，每张有 approve/redo checkpoint。见 `.claude/architecture.md`。

---

## 常用命令

```bash
# Layer 1 — 零 token 测试（mock）
powergen --mock create "topic"
powergen --mock approve
powergen --mock render

# Layer 1 — 真实 API
powergen create "topic"
powergen approve
powergen render

# Layer 1 — 交互式 REPL
powergen --mock

# Layer 2 — 零 token 测试（mock）
powergen --mock template --pptx my_template.pptx --topic "..."
```

> 任何代码路径验证都用 `--mock`，保留真实 API 调用给 prompt 质量测试。

---

## Token 成本参考

| 操作 | 模型 | 约费 |
|------|------|------|
| Layer 1 完整流程 | Haiku | ~$0.002 |
| Layer 2 v2（inventory + plan + fill） | Haiku | ~$0.003–0.01 |
| Layer 3 完整流程（8 slides + QA） | Sonnet | ~$0.10–0.30 |
| 任意层 `--mock` | — | $0.00 |
