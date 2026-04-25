# Claude Progress Log

---

## 2026-04-24 — Layer 2 v2 完成

**Branch**: `dev/powergen_layer2_ver2`

**状态**：Layer 2 Phase 1 & 2 全部完成，已 push 到 remote。

### 完成内容

**Phase 1 — 核心 pipeline**
- `inventory_gen.py`：遍历模板每张 slide，提取 shape name + text（纯代码，零 LLM token）
- `planner.py`：Composer LLM，读 inventory + topic，输出 `source_slide_index` + `text_map` 计划
- `slide_cloner.py`：按计划 clone slide，best-effort name-match fill；`_duplicate_within` 解决跨 package 污染问题
- `composer.py`：统一 3 步流程（inventory → plan → clone+fill）
- CLI：`powergen template --pptx FILE --topic "..."` / `--mock`

**Phase 2 — 质量与边界**
- 同名 shape `[N]` 索引：inventory_gen 两遍扫描，`_resolve_name` 在 fill 时解析
- Generated fallback：LLM 输出 `type: generated` 时走 `renderers/bullet.py`
- 图片保留 fix：dest_prs 从 BytesIO 完整复制，`_duplicate_within` 在同 package 内操作
- 表格只读 awareness：inventory 标注 `[TABLE] name: NxM, preview`，planner prompt 禁止填表

### 关键设计决策
- 表格不填充（Layer 2 原则：clone 模板视觉 + best-effort 文本替换；行数结构变更是 Layer 3 的职责）
- cross-package Part 污染通过"全部在 dest_prs 内操作"解决，不引用 src_prs 的 Part 对象

---

## 下一步

Layer 3 — Full Visual（未开始），见 `roadmap.md` 和 `architecture.md`。
