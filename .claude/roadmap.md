# Powergen Roadmap

## Layer 1 — Scaffold  `完成`

- Core pipeline (plan → spec → render, state machine) — 完成
- Mock client (零 token 测试) — 完成
- Interactive REPL — 完成

---

## Layer 2 — Clone + Best-effort Fill  `进行中`

> v1（Schema-Based）方案已归档于 `archive/layer2_v1_schema`。
> v2 放弃手写 schema，改用 inventory + LLM text_map 方案。见 `architecture.md`。

**Phase 1 — 核心 pipeline**
- [ ] `inventory_gen.py` — 从 .pptx 提取 slide_inventory（shape name + text，纯代码）
- [ ] `planner.py` — 重写 prompt，输入 inventory，输出 text_map 计划
- [ ] `slide_cloner.py` — 简化 fill 逻辑为 best-effort name-match 循环
- [ ] `composer.py` — 去掉 reusable/generated 分支，统一走 clone + fill
- [ ] CLI 集成（`powergen template --pptx ... --topic ...`）
- [ ] mock 模式端到端验证（用现有 test.pptx）

**Phase 2 — 质量与边界**
- [ ] 同名 shape 处理（多个同名按文本内容区分）
- [ ] Generated fallback（LLM 输出 `type: generated` 时走 renderer）
- [ ] 真实 API 测试，对比 v1 产出质量

---

## Layer 3 — Conversation Loop with Checkpoints  `未开始`

状态机：`CONTENT_PLAN → DESIGN_SPEC → SLIDE_GEN → QA_REVIEW → OUTPUT`

- [ ] 状态机骨架
- [ ] CLI REPL checkpoint（approve / edit / redo）
- [ ] 单张 slide 生成 + soffice 预览渲染
- [ ] QA 自检 loop
- [ ] Layer 2 → Layer 3 衔接（`--from-template`）
