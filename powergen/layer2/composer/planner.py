"""
Composer LLM planner: turn a schema + user topic into a plan.json dict.

The LLM sees only the semantic surface of the schema (slide names, slot keys,
content_type descriptions). It never sees locators, colors, or positions.
"""
import json
import re

_SYSTEM_PROMPT = """\
You are a presentation composer. Given a template schema and a user request, \
produce a JSON plan that specifies which slides to include and what content \
to place in each slot.

Output ONLY valid JSON — no markdown fences, no explanation.\
"""


def generate_plan(schema: dict, topic: str, client) -> dict:
    """Call the Composer LLM and return the parsed plan dict."""
    user_prompt = _build_prompt(schema, topic)
    raw = client.generate(_SYSTEM_PROMPT, user_prompt)
    return _parse_json(raw)


def mock_plan(schema: dict) -> dict:
    """Return a deterministic plan that exercises reusable + generated slides."""
    reusable = schema.get("reusable_slides", {})
    keys = list(reusable.keys())

    slides = []

    if "cover" in keys:
        slides.append({
            "type": "reusable",
            "key": "cover",
            "fill": {
                "university": "University of Toronto",
                "student_info": "路觅学生：[ 您的姓名 ]",
                "advisor_info": "路觅导师：[ 导师姓名 ]",
                "semester_label": "2026 Fall",
            },
        })

    if "section_intro" in keys:
        slides.append({
            "type": "reusable",
            "key": "section_intro",
            "fill": {
                "section_title": "课程规划",
                "section_subtitle": "Understanding your course planning options",
            },
        })

    slides.append({
        "type": "generated",
        "content_type": "bullet",
        "fill": {
            "title": "Key Course Planning Principles",
            "items": [
                "Review prerequisites before selecting courses",
                "Balance workload across semesters",
                "Consult with academic advisor regularly",
                "Track graduation requirements proactively",
            ],
        },
    })

    slides.append({
        "type": "generated",
        "content_type": "card",
        "fill": {
            "title": "Course Details",
            "items": [
                {
                    "title": "CSC207",
                    "sections": [
                        {"heading": "Overview", "body": "Software Design principles and object-oriented patterns"},
                        {"heading": "Prerequisites", "body": "CSC148 + CSC165"},
                    ],
                }
            ],
        },
    })

    slides.append({
        "type": "generated",
        "content_type": "flow",
        "fill": {
            "title": "Course Selection Process",
            "items": ["Check Prerequisites", "Review Options", "Consult Advisor", "Register Early"],
        },
    })

    if "closing_timeline" in keys:
        slides.append({
            "type": "reusable",
            "key": "closing_timeline",
            "fill": {"title": "时间线", "timeline_notes": None},
        })

    return {"title": "Course Planning Guide 2026", "slides": slides}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_prompt(schema: dict, topic: str) -> str:
    parts = [f"## Template: {schema.get('template_id', 'unknown')}\n"]

    reusable = schema.get("reusable_slides", {})
    if reusable:
        parts.append("### Reusable slides (clone + fill named slots):")
        for key, sdef in reusable.items():
            slots = sdef.get("slots", {})
            slot_parts = []
            for k, v in slots.items():
                desc = f"{k} ({v.get('kind', 'text')}"
                if v.get("max_chars"):
                    desc += f", max {v['max_chars']} chars"
                default = v.get("default")
                if default and str(default).strip():
                    preview = str(default)[:40].replace("\n", " ").replace("\v", " ")
                    desc += f", was: {preview!r}"
                desc += ")"
                slot_parts.append(desc)
            slot_summary = ", ".join(slot_parts)
            parts.append(f"- {key}: {sdef.get('purpose', '')}")
            parts.append(f"  Slots: {slot_summary}")

    generated = schema.get("generated_slides", {})
    if generated:
        parts.append("\n### Generated slide types (renderer builds from scratch):")
        for ct, gdef in generated.items():
            parts.append(
                f"- {ct}: {gdef.get('notes', '')} (max {gdef.get('max_items', '?')} items)"
            )

    hints = schema.get("compose_hints", {})
    if hints.get("ordering_rule"):
        parts.append(f"\n### Ordering: {hints['ordering_rule']}")

    parts.append(f"\n## User request:\n{topic}")

    parts.append("""
## Required output format:
{
  "title": "...",
  "slides": [
    {"type": "reusable", "key": "<key>", "fill": {"<slot_key>": "<value>"}},
    {"type": "generated", "content_type": "<type>", "fill": {"title": "...", "items": [...]}}
  ]
}

Rules:
- Only use reusable keys and content_types listed above
- For repeating slots (kind: repeating) the fill value must be a list of objects
- For optional_hint slots: use null to clear the placeholder
- Stay within max_chars limits
- Follow the ordering hint
""")

    return "\n".join(parts)


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    # strip markdown fences if present
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        raw = m.group(1).strip()
    return json.loads(raw)
