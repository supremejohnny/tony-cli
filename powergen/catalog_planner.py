from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mock_client import LLMClient

from .catalog import load_catalog_summary
from .prompts_catalog_planner import planner_system_prompt, planner_user_prompt


# ---------------------------------------------------------------------------
# Distill context loader
# ---------------------------------------------------------------------------

def _load_distill_context(distill_dir: Path) -> str:
    """Produce a compact text summary from all distill files for LLM context."""
    if not distill_dir.exists():
        return ""
    parts: list[str] = []
    for f in sorted(distill_dir.glob("*.distill.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = data.get("source", {}).get("file_name", f.stem)
        summary = data.get("global_summary", "")
        topics = ", ".join(data.get("main_topics", []))
        chunk_lines: list[str] = []
        for chunk in data.get("chunks", []):
            short = chunk.get("summary_short", "")
            if short:
                chunk_lines.append(f"  - {short}")
            for kp in chunk.get("key_points", []):
                chunk_lines.append(f"    • {kp}")
        header = f"[{name}] {summary} | Topics: {topics}"
        parts.append(header + ("\n" + "\n".join(chunk_lines) if chunk_lines else ""))
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_plan_response(raw: str) -> list[dict]:
    """Extract a JSON array from the LLM response with 3-step fallback."""
    text = raw.strip()

    # Step 1: direct parse
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    # Step 2: ```json [...] ``` fence
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group(1))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Step 3: first bare [ ... ] block
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group(0))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not parse plan response as JSON array.\nPreview:\n{raw[:500]}"
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_catalog_plan(
    brief: str,
    catalog_path: Path,
    client: "LLMClient",
    distill_dir: Path | None = None,
) -> list[dict]:
    """Phase 2: Generate an ordered slide plan from catalog + brief + distill context.

    Returns a list of slide dicts, each::

        {"pattern_id": str, "slots": {slot_name: content_value, ...}}

    The caller should pass the list to ``fill_from_plan()`` (Phase 3) to
    produce the output PPTX.
    """
    catalog_summary = load_catalog_summary(catalog_path)
    distill_context = _load_distill_context(distill_dir) if distill_dir is not None else ""
    raw = client.generate(
        planner_system_prompt(),
        planner_user_prompt(brief, catalog_summary, distill_context),
    )
    return _parse_plan_response(raw)
