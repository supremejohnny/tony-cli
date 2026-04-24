"""Call 1: template-unaware content planner.

Topic → spec IR (intent-tagged content blocks).
No knowledge of template, schema, slots, or renderers.
"""
from __future__ import annotations

import json
import re

_SYSTEM_PROMPT = """\
You are a presentation content planner. Given a topic, produce a structured outline.

Use these intent types:
  cover       — title slide (title + subtitle)
  section     — chapter divider (title + optional subtitle)
  list        — bullet points, independent items (title + items array, max 8)
  comparison  — two-side contrast (title + pairs array with left/right)
  process     — sequential steps (title + steps array, max 5)
  group       — parallel categories with equal weight (title + cards array, max 4)
  highlight   — single key point or statistic (title + body)
  closing     — final slide (title + optional body)

Output ONLY valid JSON — no markdown fences, no explanation.

Format:
{
  "title": "Presentation Title",
  "slides": [
    {"intent": "cover", "title": "...", "subtitle": "..."},
    {"intent": "section", "title": "..."},
    {"intent": "list", "title": "...", "items": ["point 1", "point 2"]},
    {"intent": "comparison", "title": "...", "pairs": [{"left": {"heading": "A", "body": "..."}, "right": {"heading": "B", "body": "..."}}]},
    {"intent": "process", "title": "...", "steps": ["Step 1", "Step 2", "Step 3"]},
    {"intent": "group", "title": "...", "cards": [{"heading": "Name", "body": "..."}, ...]},
    {"intent": "highlight", "title": "...", "body": "..."},
    {"intent": "closing", "title": "..."}
  ]
}

Rules:
- Include exactly one "cover" (first) and one "closing" (last)
- Include 1–3 "section" dividers to structure the content
- Total 8–14 slides
- Match the language of the topic
- Use "comparison" and "process" only when the content genuinely fits
"""


def generate_spec(topic: str, client) -> dict:
    """Call LLM to produce a spec IR from a topic string."""
    user_prompt = f"Topic: {topic}"
    raw = client.generate(_SYSTEM_PROMPT, user_prompt)
    return _parse_json(raw)


def mock_spec() -> dict:
    """Deterministic spec for --mock testing. Exercises all 8 intent types."""
    return {
        "title": "Course Planning Guide 2026",
        "slides": [
            {"intent": "cover", "title": "Course Planning Guide", "subtitle": "Academic Year 2026–27"},
            {"intent": "section", "title": "Why Plan Ahead", "subtitle": "Laying the groundwork for success"},
            {"intent": "list", "title": "Key Planning Principles", "items": [
                "Review prerequisites before selecting courses",
                "Balance workload across semesters",
                "Consult your academic advisor regularly",
                "Track graduation requirements proactively",
            ]},
            {"intent": "comparison", "title": "Full-time vs Part-time Study", "pairs": [{
                "left":  {"heading": "Full-time", "body": "Faster completion. Higher course load. On-campus resources."},
                "right": {"heading": "Part-time", "body": "Flexible schedule. Work-study balance. Extended timeline."},
            }]},
            {"intent": "section", "title": "Degree Requirements"},
            {"intent": "group", "title": "Core Requirement Categories", "cards": [
                {"heading": "Core CS",    "body": "Algorithms, data structures, systems programming"},
                {"heading": "Math",       "body": "Calculus, linear algebra, discrete math"},
                {"heading": "Electives",  "body": "Choose 3 from approved upper-year courses"},
                {"heading": "Capstone",   "body": "Final year research or industry project"},
            ]},
            {"intent": "process", "title": "Course Selection Process",
             "steps": ["Check Prerequisites", "Review Options", "Consult Advisor", "Register Early"]},
            {"intent": "highlight", "title": "Important Deadline",
             "body": "Course registration opens 6 weeks before semester start. Early selection guarantees seat availability."},
            {"intent": "closing", "title": "Start Planning Today",
             "body": "Your academic advisor is available Mon–Fri, 9am–5pm"},
        ],
    }


def _parse_json(raw: str) -> dict:
    raw = raw.strip()

    # Strip markdown fences if present
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        raw = m.group(1).strip()

    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fallback: extract outermost {...} block
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    # Last resort: strip trailing commas before } or ] and retry
    cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
    return json.loads(cleaned)
