from __future__ import annotations

import json


def planner_system_prompt() -> str:
    return """\
You are a presentation content planner. Given available slide patterns and a content brief, \
select which patterns to use (in order) and generate the text content for every slot.

Rules:
1. Only use pattern_id values that appear in the catalog. Never invent pattern ids.
2. "reusable": true patterns may appear multiple times (once per logical section or topic). \
   "reusable": false patterns should appear at most once.
3. Respect each slot's max_chars. Write concise, presentation-quality content.
4. "content_type": "bullets" slots — one item per line, no leading dash or bullet symbol.
5. "content_type": "text" slots — a single short phrase or sentence.
6. Use knowledge context for factual accuracy. Fall back to the brief alone if context is absent.
7. Select only the patterns that best serve the brief. Not every pattern needs to be used.
8. Output ONLY a valid JSON array — no preamble, no markdown fences, no explanation.

Required output — a JSON array where each element is:
{
  "pattern_id": "<id from catalog>",
  "slots": {
    "<slot_name>": "<content string>",
    ...
  }
}"""


def planner_user_prompt(
    brief: str,
    catalog_summary: list[dict],
    distill_context: str,
) -> str:
    catalog_str = json.dumps(catalog_summary, ensure_ascii=False, indent=2)
    context_block = (
        f"\nKnowledge context (from workspace files):\n{distill_context}\n"
        if distill_context.strip()
        else ""
    )
    return (
        f"Brief: {brief}\n\n"
        f"Available slide patterns:\n{catalog_str}\n"
        f"{context_block}\n"
        "Output a slide plan as a JSON array."
    )
