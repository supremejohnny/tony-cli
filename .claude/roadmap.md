# Powergen Roadmap

## Layer 1 — Scaffold  `完成`

- Core pipeline (plan → spec → render, state machine) — 完成
- Mock client (零 token 测试) — 完成
- Interactive REPL — 完成

---

## Layer 2 — Clone + Best-effort Fill  `进行中`

> v1（Schema-Based）方案已归档于 `archive/layer2_v1_schema`。
> v2 放弃手写 schema，改用 inventory + LLM text_map 方案。见 `architecture.md`。

**Phase 1 — 核心 pipeline** `完成`
- [x] `inventory_gen.py` — 从 .pptx 提取 slide_inventory（shape name + text，纯代码）
- [x] `planner.py` — 重写 prompt，输入 inventory，输出 text_map 计划
- [x] `slide_cloner.py` — 简化 fill 逻辑为 best-effort name-match 循环
- [x] `composer.py` — 去掉 reusable/generated 分支，统一走 clone + fill
- [x] CLI 集成（`powergen template --pptx ... --topic ...`）
- [x] mock 模式端到端验证（用现有 test.pptx）

**Phase 2 — 质量与边界** `完成`
- [x] 同名 shape 处理（`[N]` 索引，inventory_gen 两遍扫描 + _resolve_name fill）
- [x] Generated fallback（LLM 输出 `type: generated` 时走 bullet renderer）
- [x] 真实 API 测试，对比 v1 产出质量
- [x] 表格只读 awareness（inventory 标注 `[TABLE]`，planner prompt 禁止填表）

---

## Layer 3 — Conversation Loop with Checkpoints  `未开始`

状态机：`CONTENT_PLAN → DESIGN_SPEC → SLIDE_GEN → QA_REVIEW → OUTPUT`

- [ ] 状态机骨架
- [ ] CLI REPL checkpoint（approve / edit / redo）
- [ ] 单张 slide 生成 + soffice 预览渲染
- [ ] QA 自检 loop
- [ ] Layer 2 → Layer 3 衔接（`--from-template`）
