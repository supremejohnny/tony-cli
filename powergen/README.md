# PowerGen Layer 2 v0 — 归档

> **此分支已归档（`archive/layer2_v0_catalog`）**。v0（Catalog + Distiller 方案）在实现过程中暴露出根本性问题，被 v1（Schema 方案）取代。v1 随后也因类似的深层原因被放弃，最终由 v2（Inventory 方案）重写。

---

## 已实现内容

| 组件 | 职责 |
|------|------|
| `distiller.py` | 从 `.pptx` 提取文本；对图片型 slide 调用 Vision 模型描述内容 |
| `catalog.py` | 遍历模板每张 slide，输出含坐标、尺寸、类型标签的 shape 清单，交给 LLM 生成 catalog JSON |
| `catalog_planner.py` | 基于 catalog 让 LLM 规划 slide 选取和内容填充顺序 |
| `catalog_filler.py` | 按 catalog 计划克隆 slide、填充文案 |
| `dynamic_renderer.py` | 模板没有合适 slide 时的代码渲染器 |
| `theme_extractor.py` | 从 `.pptx` 提取品牌颜色和字体 |
| `.powergen_skill/distill.md` | 蒸馏流程说明文档 |
| `.powergen_catalog/` | 运行时缓存的 catalog JSON（如 `test.catalog.json`） |

**设计理念**：把模板"蒸馏"成结构化中间表示（catalog），LLM 基于 catalog 决策，代码执行填充。Vision 模型处理图片型 slide，文本型 slide 用 python-pptx 提取。

---

## 为何放弃

### 背景：在 v0 和 v1 之间存在的共同问题

v0 和 v1（schema 方案）都试图解决同一个问题：**如何把 `.pptx` 的语义高效传递给 LLM**。两者的路径不同，但都遭遇了相似的结构性困境。

---

### 问题一：Catalog 包含了模型无法有效利用的坐标信息

`catalog.py` 的 `_format_slides_for_prompt` 为每个 shape 输出：

```
[TEXT]  "TextBox 15"  pos=(1.50,2.30) 5.00x0.50in → "路觅学生：[ — ]"
[IMAGE] "图片 3"      pos=(0.00,0.00) 2.00x7.50in
[DECO]  "矩形 12"     pos=(8.50,0.10) 5.00x0.10in
```

坐标（英寸）和尺寸对人类工程师有用，可以判断"这个形状在左上角还是右下角"。但 LLM 在推理"这个 TextBox 应该填什么文案"时，完全不需要也无法有效利用这些数字——它只需要 shape 名称和当前文本。

这是**把人类读图的方式直接投射给模型**。坐标对人类是直观的视觉信息，对模型是纯数字噪音。

---

### 问题二：Vision 蒸馏成本高，且引入额外的语义损耗

`distiller.py` 对图片型 slide 的处理路径：

1. 将 slide 渲染为图片（或直接读取内嵌图片）
2. 调用 Vision 模型（如 claude-haiku 的视觉接口）描述 slide 内容
3. 把描述文字加入 catalog

问题：
- 每张含图片的 slide 多一次 Vision 调用，成本随模板复杂度线性增加
- Vision 模型对 PPT 截图的描述是**有损的**——它可能错误描述品牌颜色、忽略关键文字、混淆形状关系
- 描述的精确度取决于模型版本和截图质量，不稳定

更根本的问题：**用视觉理解来"反向工程"一个 PPTX 是绕远路**。python-pptx 已经能直接读到结构化数据，没有必要先渲染成图片再让模型重新理解。

---

### 问题三：Catalog 是另一种形式的人类结构预注入

虽然 v0 比 v1 少了很多手写字段（没有 `slot_key`、没有 `reuse_tier`、没有 locator 策略），但 catalog 的生成过程仍然需要 LLM 对 shape 清单进行"分类标注"——而这个标注结果被持久化到 `.powergen_catalog/` 下，之后的 `catalog_planner.py` 基于这个缓存进行规划。

这意味着：
- 模板的语义理解在**catalog 生成时**就被固化了
- 后续 LLM 调用看到的是 catalog 的摘要，而不是原始 shape 数据
- 如果模板更新（设计师修改了某张 slide），catalog 需要手动失效重建

与 v1 的 schema 本质相同：**一个人类（或早期 LLM）对模板的理解，被当作"事实"传递给后续的 LLM**。

---

### 问题四：两阶段架构引入了不必要的中间状态

v0 的流程是：pptx → catalog（LLM 调用）→ plan（LLM 调用）→ fill（代码）。

v2 的流程是：pptx → inventory（纯代码）→ plan + fill（单次 LLM 调用）。

v0 多了一个 LLM 调用专门生成中间 catalog，且这个 catalog 需要缓存和失效管理。这增加了系统复杂度，而收益不明显——inventory 方案证明"用代码直接提取 shape 文本"足以替代 catalog LLM。

---

### 核心教训（与 v1 共通）

> 试图把"最有利于人类理解的数据格式"（坐标、尺寸、分类标签）投射给模型，并不等于给模型"最有利于它理解的 context"。
>
> 正确的信息密度目标：**用代码去掉 XML 噪音，只保留 shape 名称 + 文本内容**。去掉坐标，去掉尺寸，去掉视觉描述——让模型基于语义而不是几何信息推断用途。

v0 的 catalog 包含了太多对模型无用的几何信息，还引入了 Vision 蒸馏的额外成本和不稳定性。

v1 的 schema 收敛了信息量，但把人类分析结论强加为约束，限制了模型的自由度。

v2 的 inventory 找到了中间点：信息密度合理（shape_name + text），模型语义推断不受约束。

---

## 对后续版本有价值的组件

| 组件 | 状态 |
|------|------|
| `distiller.py` 的文本提取路径（非 Vision 部分） | v2 `inventory_gen.py` 沿用了相同的提取逻辑 |
| `theme_extractor.py` | 保留，Layer 3 的 Design Spec 阶段需要 |
| `dynamic_renderer.py` | 改造为 v1/v2 的 `renderers/`，作为 fallback |
