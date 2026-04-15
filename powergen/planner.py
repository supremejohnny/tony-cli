from __future__ import annotations

import json
import re

from .mock_client import LLMClient
from .models import PlanDocument
from .prompts import plan_system_prompt, plan_user_prompt, revise_plan_system_prompt, revise_plan_user_prompt
from .state import ProjectState
from .workspace import WorkspaceContext


class ParseError(ValueError):
    """Raised when the LLM response cannot be parsed into a PlanDocument."""


def generate_plan(
    topic: str,
    workspace: WorkspaceContext,
    client: LLMClient,
    state: ProjectState,
) -> PlanDocument:
    """Call the LLM, parse the plan, persist it to state, and return it."""
    system = plan_system_prompt()
    user = plan_user_prompt(topic, workspace)
    raw = client.generate(system, user)
    plan = _parse_plan_response(raw)
    state.advance_to_planned(plan)
    return plan


def revise_plan(
    feedback: str,
    workspace: WorkspaceContext,
    client: LLMClient,
    state: ProjectState,
) -> PlanDocument:
    """Apply user feedback to the current plan, persist, and return the updated plan."""
    if state.plan is None:
        from .state import StateError
        raise StateError("No plan to revise. Run 'create' first.")
    system = revise_plan_system_prompt()
    user = revise_plan_user_prompt(state.plan, feedback)
    raw = client.generate(system, user)
    plan = _parse_plan_response(raw)
    state.plan = plan
    state.save()
    return plan


def _parse_plan_response(raw: str) -> PlanDocument:
    """Try to extract valid JSON from the LLM response and deserialise it."""
    text = raw.strip()

    # 1. Try direct parse
    try:
        data = json.loads(text)
        return PlanDocument.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        pass

    # 2. Extract first ```json ... ``` or ``` ... ``` block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            return PlanDocument.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass

    # 3. Extract first bare { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return PlanDocument.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            pass

    raise ParseError(
        f"Could not parse LLM response as a PlanDocument.\nResponse was:\n{raw[:500]}"
    )
