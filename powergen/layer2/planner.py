from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..mock_client import LLMClient

from .inventory_gen import format_for_prompt

_SYSTEM_PROMPT = """\
你是一个演示文稿编排器。

给你一个模板的 slide 清单（每张 slide 的 layout 名称和 shape 名称+原始文本），以及用户的主题/需求。

你的任务：
1. 从模板中选择合适的 slide，组成一份完整的演示文稿
2. 同一张 slide 可以被选多次（第二次及之后加 "clone_again": true）
3. 为每个选中 slide 中需要替换文案的 shape 编写新文本，放入 text_map

输出 JSON 格式：
{
  "title": "演示文稿标题",
  "slides": [
    {
      "source_slide_index": 0,
      "reason": "简述为什么选这张",
      "text_map": {
        "形状名称": "新文案"
      }
    },
    {
      "source_slide_index": 3,
      "clone_again": true,
      "reason": "同样版式用于第二段内容",
      "text_map": { "形状名称": "新文案" }
    }
  ]
}

规则：
- shape 名称必须和清单中完全一致（包括空格和中文）
- 不需要改动的 shape 不要放进 text_map（保留原始文本）
- 如果模板中没有合适的 slide，可输出 {"type": "generated", "content_type": "bullet", "title": "...", "items": [...]} 作为 fallback
- 直接输出 JSON，不要有任何其他文字\
"""


def build_plan(inventory: dict, topic: str, client: "LLMClient") -> dict:
    """Call the Composer LLM to produce a slide plan from the inventory + topic."""
    user_prompt = f"用户主题：{topic}\n\n模板 Slide 清单：{format_for_prompt(inventory)}"
    raw = client.generate(_SYSTEM_PROMPT, user_prompt)
    return _parse(raw)


def _parse(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Planner returned invalid JSON: {exc}\n---\n{raw[:400]}") from exc


def mock_plan(inventory: dict) -> dict:
    """Return a deterministic mock plan that exercises the clone + fill path."""
    slides = inventory.get("slides", [])
    plan_slides = []
    # Pick up to 3 slides: first, middle, last
    indices = _pick_indices(len(slides), 3)
    for i, idx in enumerate(indices):
        text_map: dict[str, str] = {}
        if slides and idx < len(slides):
            for shape in slides[idx]["shapes"][:2]:
                text_map[shape["name"]] = f"[Mock] {shape['text'][:40]}"
        entry: dict = {"source_slide_index": idx, "reason": f"mock slide {i + 1}"}
        if i > 0:
            entry["clone_again"] = True
        if text_map:
            entry["text_map"] = text_map
        plan_slides.append(entry)

    return {"title": "Mock AI Presentation", "slides": plan_slides}


def _pick_indices(n: int, count: int) -> list[int]:
    if n == 0:
        return []
    if n == 1:
        return [0]
    step = max(1, (n - 1) // (count - 1)) if count > 1 else 1
    indices = list(range(0, n, step))[:count]
    return indices
