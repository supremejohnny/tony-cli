# Layer 2 v1 — 归档

> **此分支已归档（`archive/layer2_v1_schema`）**。v1 在完整实现后因根本性设计缺陷被放弃，继任方案为 Layer 2 v2（`dev/powergen_layer2_v2`）。

---

## 已实现内容

完整的 schema 驱动模板组合系统，三角色架构：

| 组件 | 职责 |
|------|------|
| `schema_gen.py` | 从 `.pptx` 提取形状信息，生成初始 schema 草稿 |
| `schema_loader.py` | 加载并验证 schema JSON，去除 `_comment` 字段 |
| `slot_resolver.py` | 通过 `shape_name` / `nth` / `near` 三级策略精确定位目标形状 |
| `slide_cloner.py` | clone 模板 slide，按 slot 定义填充文本（lxml + OPC 层） |
| `composer.py` + `planner.py` | LLM 驱动的 slide 选择 + 文案生成 |
| `renderers/*` | 各 `content_type` 的代码渲染器（card, bullet, flow 等） |
| `SKILL.md` | 560 行 schema 编写指南，含 6 步编写流程 |
| `schemas/test_template.schema.json` | 针对 `test.pptx` 的 300 行手写 schema |

**设计理念**：LLM 只看 schema 的语义面（slide 名称、slot key），不接触颜色/字体/坐标；代码层负责执行；视觉参数封装在 design tokens 里。三者职责清晰，理论上可维护。

---

## 为何放弃

### 根本问题：Context Engineering 的结构性困境

与 LLM 协作时，如何传递 `.pptx` 的内容是核心挑战：

- **过于原始**：直接喂 OOXML。一张 slide 的 XML 可达 10,000+ token，充满格式噪音，成本不可接受。
- **过于结构化**：人工将模板语义压缩成 JSON schema（slot_key、kind、reuse_tier、locator…）。这是 v1 的选择。

v1 的问题在于，选了"过于结构化"，实质上是**让人类替 LLM 做了所有语义分析，再把结论以封闭 JSON 的形式注入**。这不是在帮助模型，而是在把人类对模板的片面理解固化为模型的思维边界。

---

### 问题一：schema 编写成本极高，与"零配置"目标矛盾

`SKILL.md` 记录了 6 步手动流程：

1. 对每张 slide 分类（Reusable / Generated / Skip）
2. 过 overfitting filter（reuse_tier 分级：`pattern` vs `template_local`）
3. 为每个 slot 定义 kind（text / multiline / repeating / image / optional_hint）
4. 处理 repeating 组（`stride_y`/`stride_x` 间距计算）
5. 提取 design tokens
6. 运行 `validate.py` 校验所有 locator 可解析

一个新模板需要 **2–4 小时人工 schema 编写**。配置成本从机器转移给了人。

---

### 问题二：人类抽象 ≠ 模型最优抽象

Schema 里充满了人类逻辑的产物，对模型来说是冗余的间接层：

- `reuse_tier: "pattern" | "template_local"` — 人类对可复用程度的判断，模型不需要知道
- `stride_y: 2.44` — 人类计算的 repeating 组件间距（英寸），模型从不消费这个数字
- `nth: 0` / `nth: 1` / `near: {top, left}` — 解决重名 shape 的定位策略，是人类的工程问题
- `compose_hints.ordering_rule` — 人类总结的 slide 排序规则，写死在 schema 里

这些抽象让 LLM 的决策空间变成了封闭枚举：从 N 个 reusable + M 个 content_type 中选。

但代价是：LLM **只能沿人类预设的轨道运行**。若模板不符合预设分类，模型无法自适应。

对比 v2 的 `slide_inventory`：LLM 直接看到 shape_name + 原始文本，靠自身语义理解判断每个 shape 的用途。它不需要 `kind: "optional_hint"` 来识别"老师请介绍...（阅后删除）"是提示文本——它自己能看出来。

---

### 问题三：locator 复杂度是自己制造的问题

`slot_resolver.py` 有三级 locator 策略（`shape_name` → `+nth` → `+near`）以及 `stride` 计算逻辑。

这套复杂度的根源：为了把人类定义的 `slot_key`（如 `"student_info"`）映射到具体形状（"第 0 个 TextBox 15"），需要一套精确的寻址机制。

如果 LLM 直接用 shape_name + 原始文本识别形状，"两个 TextBox 15，一个写学生、一个写导师"凭文本即可区分，`nth: 0 / nth: 1` 的人工标注完全不需要。

---

### 问题四：schema 对特定场景严重过拟合

`test_template.schema.json` 的 reusable slide 类型（`cover`、`mentor_intro`、`section_intro`、`numbered_card_grid_v/h`、`closing_timeline`）是为**留学咨询课程规划**这一特定场景定制的分类体系。

对销售 deck、技术路线图、医疗汇报等其他类型的模板，这套分类几乎完全失效，每种新场景都需要重新定义一套 slot 语义。Schema 的"跨模板复用"是名义上的。

---

### 核心教训

> 不要用人类对"模型最能理解的格式"的猜测来预处理 context。
>
> 正确路径：用代码做信息密度压缩（去掉 XML 噪音，只保留 shape name + 文本），让模型在密度合理的 context 上自由推断——而不是在人类精心设计的封闭类目里被约束。

v1 的 schema 是一条人类精心设计的窄道。v2 的 `slide_inventory` 是信息密度合理的开阔地。

---

## 保留到 v2 的内容

| 组件 | 处理方式 | 原因 |
|------|----------|------|
| `slide_cloner.py` clone 核心 | 保留 | 品牌视觉保留的关键机制 |
| `renderers/*` | 保留，作为 fallback | 模板无合适 slide 可 clone 时使用 |
| `schema_gen.py` shape 提取逻辑 | 改造为 `inventory_gen.py` | 只输出 shape_name + text，去掉全部 slot/kind 字段 |

其余删除：`schema_loader.py`、`slot_resolver.py`、`validate.py`、`SKILL.md`（大部分）、手写 schema JSON。
