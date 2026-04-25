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

## Layer 3 — Compositional Deck Generation  `未开始`

状态机：`CONTENT_PLAN → SLIDE_GEN → QA → OUTPUT`
设计原则：layout × block 组合系统；DESIGN_SPEC 降级为隐式 style context；无 per-slide loop。
见 `architecture.md` 完整设计。

**Phase 1 — 组合 spec + python-pptx 渲染**
- [ ] 状态机骨架（`composer.py`）+ CLI 接入（`powergen generate`）
- [ ] `planner.py` — LLM: topic → slide list（purpose + key_message）
- [ ] `spec_builder.py` — LLM: slide list → compositional spec（layout + blocks）
- [ ] `renderer.py` 抽象层 + `renderers/pptx.py` — 4 layouts × 5 block types
- [ ] `qa.py` — 组合合理性检查（density / overflow / block 搭配规则）
- [ ] mock 端到端验证

**Phase 2 — HTML / Playwright 渲染后端**
- [ ] HTML layout templates（4 layouts，受限 CSS subset）
- [ ] Playwright pipeline：render → getBoundingClientRect → EMU → python-pptx shapes
- [ ] `renderers/browser.py` — 接入同一 spec，替换渲染后端
- [ ] 字体锁定 + viewport 固定（防 layout drift）
- [ ] 对比 Phase 1 产出质量
