from __future__ import annotations

import json
import re

from .mock_client import LLMClient
from .models import PlanDocument, PresentationSpec, SlideSpec
from .prompts import spec_system_prompt, spec_user_prompt
from .workspace import WorkspaceContext


class ParseError(ValueError):
    """Raised when the LLM response cannot be parsed into a PresentationSpec."""


def build_spec(
    plan: PlanDocument,
    workspace: WorkspaceContext,
    client: LLMClient,
) -> PresentationSpec:
    """Convert an approved PlanDocument into a PresentationSpec via LLM."""
    all_layouts: list[str] = []
    for tmpl in workspace.templates:
        all_layouts.extend(tmpl.layouts)

    system = spec_system_prompt(all_layouts)
    user = spec_user_prompt(plan, workspace)
    raw = client.generate(system, user)
    return _parse_spec_response(raw)


def _parse_spec_response(raw: str) -> PresentationSpec:
    """Extract valid JSON from LLM response and deserialise into PresentationSpec."""
    text = raw.strip()

    # 1. Try direct parse
    try:
        data = json.loads(text)
        return _build_spec_from_dict(data)
    except (json.JSONDecodeError, KeyError):
        pass

    # 2. Extract ```json ... ``` or ``` ... ``` block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            return _build_spec_from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass

    # 3. Extract first bare { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return _build_spec_from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass

    raise ParseError(
        f"Could not parse LLM response as a PresentationSpec.\nResponse was:\n{raw[:500]}"
    )


def _build_spec_from_dict(data: dict) -> PresentationSpec:
    slides = [SlideSpec.from_dict(s) for s in data.get("slides", [])]
    return PresentationSpec(
        title=data["title"],
        audience=data.get("audience", ""),
        tone=data.get("tone", "professional"),
        theme_reference=data.get("theme_reference", ""),
        slides=slides,
    )
