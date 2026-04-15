from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# Slide type vocabulary (shared with renderer)
# ---------------------------------------------------------------------------

SLIDE_TYPES: dict[str, str] = {
    "title":              "Cover slide — maps to a template special slide",
    "section_divider":    "Chapter/section break — dark background, large centered title",
    "content_simple":     "Bullet list (up to 8 bullets, each one short phrase)",
    "content_structured": "Structured cards — each point has a bold title + description (2–6 points)",
    "two_column":         "Left/right comparison — two independent columns of content",
    "timeline":           "Numbered steps or process flow (3–6 steps)",
    "special":            "Template-unique slide (profile, contact, etc.) — must exist in template",
}

# JSON schemas that Claude should follow per type
_TYPE_SCHEMAS = {
    "title": '{"type": "title", "special_slide": "<slide_id>", "slots": {"title": "...", "subtitle": "..."}}',
    "section_divider": '{"type": "section_divider", "title": "...", "subtitle": "..."}',
    "content_simple": '{"type": "content_simple", "title": "...", "bullets": ["...", "..."]}',
    "content_structured": '{"type": "content_structured", "title": "...", "points": [{"title": "...", "desc": "..."}, ...]}',
    "two_column": '{"type": "two_column", "title": "...", "left": {"heading": "...", "bullets": ["..."]}, "right": {"heading": "...", "bullets": ["..."]}}',
    "timeline": '{"type": "timeline", "title": "...", "steps": [{"label": "...", "desc": "..."}, ...]}',
    "special": '{"type": "special", "special_slide": "<slide_id>", "slots": {"<slot_name>": "..."}}',
}


def generator_system_prompt(
    available_special_slides: list[str],
) -> str:
    type_lines = "\n".join(
        f"  {t}: {desc}" for t, desc in SLIDE_TYPES.items()
    )
    schema_lines = "\n\n".join(
        f"  {t}:\n    {schema}" for t, schema in _TYPE_SCHEMAS.items()
    )
    special_list = json.dumps(available_special_slides, ensure_ascii=False)

    has_special = bool(available_special_slides)
    special_constraint = (
        f'These are the ONLY valid values for "special_slide". '
        f'If a type is "title" or "special", "special_slide" MUST be one of these values.'
        if has_special else
        "No special slides are available — do NOT use type \"title\" or \"special\" at all."
    )
    opening_rule = (
        '1. Always start with a "title" slide using the "title" special_slide (if available).'
        if has_special else
        '1. Start with a "section_divider" slide as the cover/title (no special slides available).'
    )

    return f"""\
You are a slide content planner. Generate a structured typed slide plan as a JSON array.

## Available slide types

{type_lines}

## JSON schema per type

{schema_lines}

## Template special slides available

{special_list}

{special_constraint}

## Rules

{opening_rule}
2. Use "special" or "title" only for slide_ids listed in the template special slides above.
3. Content rules for "content_structured":
   - 2 points → side-by-side comparison (best for contrasts)
   - 3–4 points → grid cards
   - 5+ points → use "content_simple" (bullet list) instead
4. Vary layouts — avoid two consecutive slides of the same type.
5. Each slide must have a clear, single purpose. No wall-of-text slides.
6. "bullets" lists: each bullet is a short phrase (≤15 words), no leading dash or symbol.
7. Respect the language of the brief — write ALL content in that language.
8. Produce 8–14 slides for a standard brief (unless the brief implies otherwise).
9. Output ONLY a valid JSON array — no preamble, no markdown fences, no explanation."""


def generator_user_prompt(
    brief: str,
    available_special_slides: list[str],
    distill_context: str,
) -> str:
    special_list = ", ".join(available_special_slides) if available_special_slides else "(none)"
    context_block = (
        f"\nKnowledge context (from workspace files):\n{distill_context}\n"
        if distill_context.strip()
        else ""
    )
    return (
        f"Brief: {brief}\n\n"
        f"Template special slides: {special_list}\n"
        f"{context_block}\n"
        "Output a slide plan as a JSON array."
    )
