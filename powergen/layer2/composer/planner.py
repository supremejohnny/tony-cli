"""
Composer LLM planner: turn a schema + user topic into a plan.json dict.

The LLM sees only the semantic surface of the schema (slide names, slot keys,
content_type descriptions). It never sees locators, colors, or positions.

If the schema has been annotated (slot_label / confidence fields present from
annotator.py), those labels are surfaced in the prompt to improve fill quality.
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
            composable = sdef.get("composable", True)
            decorative_heavy = sdef.get("decorative_heavy", False)

            suffix = ""
            if not composable:
                reason = sdef.get("composable_reason", "non-composable")
                suffix = f" [NON-COMPOSABLE ({reason}) — use fill: {{}}]"
            elif decorative_heavy:
                suffix = " [decorative-heavy — use fill: {}]"

            parts.append(f"- {key}: {sdef.get('purpose', '')}{suffix}")

            # For non-composable or decorative slides, don't expand slots
            if not composable or decorative_heavy:
                continue

            slots = sdef.get("slots", {})
            fillable_slots = [(k, v) for k, v in slots.items() if not v.get("visual_only")]
            if not fillable_slots:
                continue

            parts.append('  Fill keys — use these EXACT strings as JSON keys in "fill":')
            for k, v in fillable_slots:
                kind = v.get("kind", "text")
                slot_label = v.get("slot_label", "")
                confidence = v.get("confidence", "")

                meta_parts = []
                if slot_label:
                    label_str = slot_label
                    if confidence:
                        label_str += f"/{confidence}"
                    meta_parts.append(label_str)
                meta_parts.append(kind)

                if kind == "table":
                    default = v.get("default", [])
                    rows = len(default)
                    cols = len(default[0]) if rows and default[0] else 0
                    meta_parts.append(f"{rows}×{cols} table — value: list of lists")
                else:
                    default = v.get("default")
                    if default and str(default).strip():
                        preview = str(default)[:50].replace("\n", " ").replace("\v", " ")
                        meta_parts.append(f'was: "{preview}"')

                parts.append(f'    "{k}": {" | ".join(meta_parts)}')

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
    {"type": "reusable", "key": "slide_0", "fill": {"object 2": "new text", "object 9": "Company Name"}},
    {"type": "reusable", "key": "slide_1", "fill": {}},
    {"type": "generated", "content_type": "bullet", "fill": {"title": "...", "items": [...]}}
  ]
}

CRITICAL RULES:
1. Fill key strings MUST be copied EXACTLY from the "Fill keys" list above — including spaces and numbers.
   WRONG: {"title": "..."}, {"company": "..."}
   RIGHT: {"object 2": "..."}, {"object 9": "..."}
2. Only include slides and slot keys from the lists above.
3. For table slots: value must be a list of lists (2D array matching original dimensions).
4. For NON-COMPOSABLE and decorative-heavy slides: use fill: {}
5. Follow the ordering hint.
""")

    return "\n".join(parts)


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        raw = m.group(1).strip()
    return json.loads(raw)
