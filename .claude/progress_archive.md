# Progress Archive

历史 session 压缩归档。仅回溯决策时查阅。

---

## Layer 2 v1（Schema-Based）— 已归档

**Branch**: `archive/layer2_v1_schema`（原 `dev/powergen_layer2_ver1`）

**共 9 个 session**，完整实现了 schema 驱动的三角色架构（Composer LLM + Composer code + Renderers）。
主要模块：`schema_gen.py`、`schema_loader.py`、`slot_resolver.py`、`slide_cloner.py`、`composer.py`、`planner.py`、`renderers/*`、`annotator.py`、`compiler.py`、`spec.py`。

**放弃原因**：Context engineering 结构性困境——人工 schema 把人类对模板的理解固化为模型的思维边界，配置成本高（560 行 SKILL.md，每模板 2–4 小时），且对特定场景过拟合。
详见 `archive/layer2_v1_schema` 的 `powergen/layer2/README.md`。

---

## Layer 2 v0（Catalog + Distiller）— 已归档

**Branch**: `archive/layer2_v0_catalog`（原 `dev/powergen`）

使用 `distiller.py`（Vision OCR）+ `catalog.py`（含坐标的 shape 清单）方案。
放弃原因：坐标信息对 LLM 文案决策无用；Vision 蒸馏成本高且有损；catalog 是另一种形式的人类结构预注入。
详见 `archive/layer2_v0_catalog` 的 `powergen/README.md`。

---

## Layer 1 — 完成

**Branch**: merged to `main`（commit `b06107e`）

完整的 Layer 1 Scaffold pipeline：plan → spec → render，状态机，mock client，interactive REPL。
