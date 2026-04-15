from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mock_client import LLMClient

from .catalog import load_available_special_slide_ids
from .prompts_content_generator import generator_system_prompt, generator_user_prompt


# ---------------------------------------------------------------------------
# Distill context loader (same logic as catalog_planner)
# ---------------------------------------------------------------------------

def _load_distill_context(distill_dir: Path) -> str:
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
    text = raw.strip()

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group(1))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group(0))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not parse content plan as JSON array.\nPreview:\n{raw[:500]}"
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_VALID_TYPES = {
    "title", "section_divider", "content_simple",
    "content_structured", "two_column", "timeline", "special",
}


def _validate_plan(plan: list[dict], available_special: list[str]) -> list[dict]:
    """Drop entries with invalid types or unknown special_slide references.
    Prints warnings for skipped entries.
    """
    special_set = set(available_special)
    valid: list[dict] = []
    for entry in plan:
        t = entry.get("type", "")
        if t not in _VALID_TYPES:
            print(f"  Warning: unknown slide type '{t}', skipping.")
            continue
        if t in ("title", "special"):
            sid = entry.get("special_slide", "")
            if sid not in special_set:
                print(f"  Warning: special_slide '{sid}' not in template, skipping.")
                continue
        valid.append(entry)
    return valid


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_content_plan(
    brief: str,
    catalog_path: Path,
    client: "LLMClient",
    distill_dir: Path | None = None,
) -> list[dict]:
    """Generate a typed slide plan from a brief + catalog metadata.

    Returns a list of slide dicts, e.g.::

        [
          {"type": "title", "special_slide": "title", "slots": {"title": "..."}},
          {"type": "section_divider", "title": "..."},
          {"type": "content_structured", "title": "...", "points": [...]},
        ]
    """
    available_special = load_available_special_slide_ids(catalog_path)
    distill_context = _load_distill_context(distill_dir) if distill_dir is not None else ""

    sys_prompt = generator_system_prompt(available_special)
    usr_prompt = generator_user_prompt(brief, available_special, distill_context)

    raw = client.generate(sys_prompt, usr_prompt)
    plan = _parse_plan_response(raw)
    plan = _validate_plan(plan, available_special)
    return plan
