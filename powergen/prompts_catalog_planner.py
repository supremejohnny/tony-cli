from __future__ import annotations

import json


def planner_system_prompt() -> str:
    return """\
You are a presentation content planner. Given a template catalog and a content brief, \
produce an ordered list of slide operations that will build the final presentation.

## Operation types

  fill_special   — Fill a one-time template slide (cover, profile, contact, etc.) using
                   its named slots. Use for slides listed in special_slides.

  keep           — Include a template slide exactly as-is, with no text changes. Use when
                   the slide's existing content is still accurate and relevant for the brief.

  clone_pattern  — Deep-copy a reusable template slide and fill it with new content.
                   Use for slides listed in patterns. The same pattern_id may appear
                   multiple times (once per section or topic).

## Output schema

A JSON array where each element is exactly ONE of:

  {"op": "fill_special", "slide_id": "<id from special_slides>",
   "slots": {"<slot_name>": "<content>", ...}}

  {"op": "keep", "source_slide": <int, 1-based>}

  {"op": "clone_pattern", "pattern_id": "<id from patterns>",
   "slots": {"<slot_name>": "<content>", ...}}

## Rules

1. Always start with fill_special for the "title" special slide (if available).
2. fill_special: only use slide_id values that exist in special_slides. Never invent.
3. keep: only use source_slide numbers that exist in the template (1-based integer).
4. clone_pattern: only use pattern_id values that exist in patterns. Never invent.
5. clone_pattern may repeat with the same pattern_id — one clone per topic/section.
6. Avoid more than 3 consecutive clone_pattern operations with the same pattern_id.
7. For content_type "text": write a single concise line, max given max_chars.
8. For content_type "bullets": write one item per line, no leading dash or symbol.
9. Match the language of the brief for all generated content.
10. Select operations that serve the brief — not all template slides need to appear.
11. Use "keep" when an existing slide's content is generic or still applies to the brief.
    Use "clone_pattern" when you need new content for a fresh section.
12. Output ONLY a valid JSON array — no preamble, no markdown fences, no explanation."""


def planner_user_prompt(
    brief: str,
    catalog_for_planner: dict,
    distill_context: str,
) -> str:
    catalog_str = json.dumps(catalog_for_planner, ensure_ascii=False, indent=2)
    context_block = (
        f"\nKnowledge context (from workspace files):\n{distill_context}\n"
        if distill_context.strip()
        else ""
    )
    return (
        f"Brief: {brief}\n\n"
        f"Template catalog:\n{catalog_str}\n"
        f"{context_block}\n"
        "Output a slide operation plan as a JSON array."
    )
