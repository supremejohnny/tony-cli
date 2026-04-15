from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .workspace import WorkspaceContext

# ---------------------------------------------------------------------------
# Template analysis prompts
# ---------------------------------------------------------------------------

_ANALYSIS_SCHEMA = """{
  "slides": [
    {
      "slide_index": 1,
      "slide_relevant": true,
      "text_nodes": [
        {
          "original_text": "<exact text as it appears in the template>",
          "purpose": "<title|body|bullet|skip>"
        }
      ]
    }
  ]
}"""


def template_analysis_system_prompt() -> str:
    return f"""\
You are a presentation analyst. You will receive a text dump of a PowerPoint template,
slide by slide. Your job is to identify every text node and classify its purpose,
and to decide whether each slide should receive new content.

slide_relevant values:
- true: This is a real content slide that should be filled with new content
         (e.g. title slide, section content, agenda, summary)
- false: This slide is structural and must remain unchanged
          (e.g. template instructions, "how to use this template", dividers,
           navigation placeholders, blank spacer slides)

Purpose values:
- title: The main heading of a slide
- body: A paragraph or descriptive text block (not a bullet list)
- bullet: A list item or bullet point
- skip: Decorative, structural, or branding text that must NOT be changed
         (e.g. company name, logo text, footer, slide number, copyright notice,
          section labels that are part of the template design)

Rules:
- Preserve the exact original_text string character-for-character.
- When in doubt about whether text is decorative, classify it as "skip".
- When in doubt about whether a slide is structural, set slide_relevant to false.
- Every text node you see must appear in the output — do not drop any.
- No markdown fences, no extra commentary — just the JSON object.

Respond with ONLY a JSON object matching this schema:
{_ANALYSIS_SCHEMA}"""


def template_analysis_user_prompt(markitdown_output: str) -> str:
    return f"""\
Template text dump (slide by slide):

{markitdown_output}

Classify every text node."""


# ---------------------------------------------------------------------------
# Content mapping prompts
# ---------------------------------------------------------------------------

_MAPPING_SCHEMA = """{
  "mappings": [
    {
      "slide_index": 1,
      "original_text": "<exact text from template>",
      "replacement_text": "<new content>"
    }
  ]
}"""


def content_mapping_system_prompt() -> str:
    return f"""\
You are a presentation writer. You will receive:
1. A user's content brief describing what the presentation should cover.
2. A structured analysis of a PowerPoint template (slide indices, slide_relevant flags, text nodes, purposes).
3. Workspace context (available files that may inform the content).

Your job: for every text node NOT classified as "skip" on a relevant slide, generate replacement text.

Rules:
- Only generate mappings for slides where slide_relevant is true.
- Do NOT generate any mappings for slides where slide_relevant is false — leave those slides untouched.
- Only include nodes with purpose "title", "body", or "bullet" in your output.
- Keep replacement length proportional to the original:
  - Short titles (1-6 words) → replace with a similarly short title.
  - Body paragraphs → replace with a paragraph of similar length.
  - Bullets → replace with a bullet of similar brevity.
- Do NOT convert a bullet into a paragraph or a title into a sentence.
- Make the content directly relevant to the user's brief.
- Use the workspace context to inform specifics where relevant.
- No markdown fences, no extra commentary — just the JSON object.

Respond with ONLY a JSON object matching this schema:
{_MAPPING_SCHEMA}"""


def content_mapping_user_prompt(
    brief: str,
    template_analysis: dict,
    workspace: "WorkspaceContext",
) -> str:
    ws_lines = "\n".join(workspace.summary_lines())
    return f"""\
Brief: {brief}

Template analysis:
{json.dumps(template_analysis, indent=2, ensure_ascii=False)}

Workspace:
{ws_lines}

Generate replacement text for all non-skip nodes."""
