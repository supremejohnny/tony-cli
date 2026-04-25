from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..mock_client import LLMClient

from . import inventory_gen, planner, slide_cloner


def run(
    template_path: Path,
    topic: str,
    output_path: Path,
    client: "LLMClient",
    mock: bool = False,
) -> Path:
    """Full Layer 2 v2 pipeline: inventory → plan → clone + fill."""
    print("[1/3] Extracting slide inventory…")
    inventory = inventory_gen.generate(template_path)
    n_slides = len(inventory["slides"])
    print(f"      {n_slides} slides found in template.")

    print("[2/3] Planning content…")
    if mock:
        plan = planner.mock_plan(inventory)
    else:
        plan = planner.build_plan(inventory, topic, client)

    title = plan.get("title", "Untitled")
    n_plan = len(plan.get("slides", []))
    print(f"      Plan: {n_plan} slides → '{title}'")

    print("[3/3] Cloning and filling…")
    slide_cloner.compose(template_path, plan, output_path)

    return output_path


def default_output_path(template_path: Path) -> Path:
    return template_path.parent / (template_path.stem + "-filled.pptx")
