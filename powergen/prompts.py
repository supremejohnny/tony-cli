from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import PlanDocument
    from .workspace import WorkspaceContext

# ---------------------------------------------------------------------------
# Plan generation prompts
# ---------------------------------------------------------------------------

_PLAN_SCHEMA = """{
  "overview": "<1-2 sentence summary of the presentation>",
  "slide_summaries": [
    "<one sentence describing slide 1>",
    "<one sentence describing slide 2>",
    "..."
  ],
  "references": ["<filename of any workspace file you plan to draw from>"],
  "open_questions": ["<anything unclear that you'd want the user to clarify>"]
}"""


def plan_system_prompt() -> str:
    return f"""\
You are a presentation strategist. Given a topic and workspace context, produce a
concise presentation plan.

Respond with ONLY a JSON object that matches this exact schema:
{_PLAN_SCHEMA}

Rules:
- Include between 4 and 12 slides (title + content + closing).
- Each slide_summary is one sentence describing the slide's purpose and main message.
- references lists only filenames that exist in the workspace context.
- open_questions lists things the user should clarify; leave as [] if none.
- No markdown fences, no extra commentary — just the JSON object."""


def plan_user_prompt(topic: str, workspace: "WorkspaceContext") -> str:
    ws_lines = "\n".join(workspace.summary_lines())
    return f"""\
Topic: {topic}

Workspace:
{ws_lines}

Generate a presentation plan for the topic above."""


# ---------------------------------------------------------------------------
# Plan revision prompts
# ---------------------------------------------------------------------------

def revise_plan_system_prompt() -> str:
    return f"""\
You are a presentation strategist. You will receive an existing presentation plan
and user feedback. Update the plan to incorporate the feedback.

Respond with ONLY a JSON object that matches this exact schema:
{_PLAN_SCHEMA}

Rules:
- Apply the feedback precisely; do not change parts not mentioned.
- Keep slide_summaries concise (one sentence each).
- No markdown fences, no extra commentary — just the JSON object."""


def revise_plan_user_prompt(current_plan: "PlanDocument", feedback: str) -> str:
    return f"""\
Current plan:
{json.dumps(current_plan.to_dict(), indent=2, ensure_ascii=False)}

User feedback: {feedback}

Return the revised plan as JSON."""


# ---------------------------------------------------------------------------
# Spec generation prompts
# ---------------------------------------------------------------------------

_SPEC_SCHEMA = """{
  "title": "<presentation title>",
  "audience": "<target audience>",
  "tone": "<professional | casual | technical | inspirational>",
  "theme_reference": "<template filename or empty string>",
  "slides": [
    {
      "index": 0,
      "title": "<slide title>",
      "bullets": ["<bullet 1>", "<bullet 2>"],
      "layout": "<layout name>",
      "notes": "<speaker notes>"
    }
  ]
}"""


def spec_system_prompt(layouts: list[str]) -> str:
    layout_hint = ""
    if layouts:
        formatted = "\n".join(f"  - {name}" for name in layouts)
        layout_hint = f"\nAvailable template layouts (use these exact names):\n{formatted}\n"
    else:
        layout_hint = (
            "\nNo template provided. Use these generic layout names:\n"
            "  - Title Slide\n"
            "  - Title and Content\n"
            "  - Section Header\n"
            "  - Two Content\n"
            "  - Blank\n"
        )

    return f"""\
You are a presentation designer. Convert the given presentation plan into a
detailed, structured slide specification.
{layout_hint}
Respond with ONLY a JSON object that matches this exact schema:
{_SPEC_SCHEMA}

Rules:
- Each slide must have a clear, concise title (≤8 words).
- bullets: 3–5 short phrases per content slide; empty list for title/section slides.
- notes: 1–3 sentences of speaker guidance.
- Choose layout names from the list above.
- No markdown fences, no extra commentary — just the JSON object."""


def spec_user_prompt(plan: "PlanDocument", workspace: "WorkspaceContext") -> str:
    ws_lines = "\n".join(workspace.summary_lines())
    return f"""\
Plan:
{json.dumps(plan.to_dict(), indent=2, ensure_ascii=False)}

Workspace:
{ws_lines}

Generate the full slide specification."""
