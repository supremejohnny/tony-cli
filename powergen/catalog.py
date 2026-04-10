from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mock_client import LLMClient
    from .workspace import WorkspaceContext

from .prompts_catalog import catalog_system_prompt, catalog_user_prompt

# Only template PPTX files are cataloged
_PPTX_EXT = ".pptx"


# ---------------------------------------------------------------------------
# Shape formatting helpers
# ---------------------------------------------------------------------------

def _emu(v: int) -> float:
    return round(v / 914400, 2)


def _shape_tag(shape) -> str:
    """Classify a shape into TEXT / IMAGE / GROUP / DECO."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE  # type: ignore[import]
    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
        return "IMAGE"
    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        return "GROUP"
    if shape.has_text_frame and shape.text_frame.text.strip():
        return "TEXT"
    return "DECO"


def _format_slides_for_prompt(path: Path) -> str:
    """Produce a compact text representation of all slides for the LLM prompt."""
    from pptx import Presentation  # type: ignore[import]

    prs = Presentation(str(path))
    lines: list[str] = []

    for i, slide in enumerate(prs.slides, 1):
        lines.append(f'Slide {i} | layout: "{slide.slide_layout.name}"')
        for shape in slide.shapes:
            tag = _shape_tag(shape)
            name = shape.name
            pos = (
                f"pos=({_emu(shape.left)},{_emu(shape.top)}) "
                f"{_emu(shape.width)}x{_emu(shape.height)}in"
            )
            if tag == "TEXT":
                text = shape.text_frame.text.strip()[:80].replace("\n", " | ")
                lines.append(f'  [TEXT]  "{name}"  {pos} → "{text}"')
            elif tag == "IMAGE":
                lines.append(f'  [IMAGE] "{name}"  {pos}')
            elif tag == "GROUP":
                lines.append(f'  [GROUP] "{name}"  {pos}')
            else:
                lines.append(f'  [DECO]  "{name}"  {pos}')
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_catalog_response(raw: str, label: str) -> list[dict]:
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
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # Step 3: first bare [ ... ] block
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not parse {label} catalog response as JSON array.\n"
        f"Response preview:\n{raw[:500]}"
    )


# ---------------------------------------------------------------------------
# Hashing / cache check
# ---------------------------------------------------------------------------

def _compute_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _is_current(catalog_path: Path, file_hash: str) -> bool:
    if not catalog_path.exists():
        return False
    try:
        existing = json.loads(catalog_path.read_text(encoding="utf-8"))
        return existing.get("source", {}).get("file_hash", "") == file_hash
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Schema normalization
# ---------------------------------------------------------------------------

def _normalize_pattern(p: dict, slide_number: int) -> dict:
    """Ensure consistent field names regardless of what the model output."""
    # Normalize slide number field: slide_number → source_slide
    if "source_slide" not in p:
        p["source_slide"] = p.pop("slide_number", slide_number)
    # Drop unknown top-level keys that add no value downstream
    p.pop("pattern_name", None)
    return p


# ---------------------------------------------------------------------------
# Catalog readers (two-layer: summary vs full)
# ---------------------------------------------------------------------------

_SUMMARY_KEYS = {"pattern_id", "source_slide", "description", "fit_for", "not_fit_for", "reusable"}


def load_catalog_summary(catalog_path: Path) -> list[dict]:
    """Return patterns with slots stripped — used by Phase 2 planner for pattern selection.

    Sending only ~5 fields per pattern instead of full slot lists can cut Phase 2
    input tokens by 60–80 % on complex templates.
    """
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    return [
        {k: v for k, v in p.items() if k in _SUMMARY_KEYS}
        for p in data.get("patterns", [])
    ]


_SLOT_KEYS = {"shape_name", "name", "content_type", "max_chars"}


def load_catalog_slots(catalog_path: Path, pattern_ids: list[str]) -> list[dict]:
    """Return full slot details for *pattern_ids* only — used by Phase 3 filler.

    Only the patterns the planner selected are loaded, and slot descriptions are
    stripped (shape_name / name / content_type / max_chars are sufficient for filling).
    """
    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    id_set = set(pattern_ids)
    result = []
    for p in data.get("patterns", []):
        if p.get("pattern_id") not in id_set:
            continue
        p = dict(p)
        p["slots"] = [{k: v for k, v in s.items() if k in _SLOT_KEYS} for s in p.get("slots", [])]
        result.append(p)
    return result


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def extract_catalog(path: Path, client: "LLMClient") -> dict:
    """Analyze a template PPTX and return its Pattern Catalog as a dict."""
    slides_repr = _format_slides_for_prompt(path)
    raw = client.generate(catalog_system_prompt(), catalog_user_prompt(path.name, slides_repr))
    patterns = _parse_catalog_response(raw, path.name)

    # Normalize field names regardless of model output variance
    patterns = [_normalize_pattern(p, i + 1) for i, p in enumerate(patterns)]

    return {
        "version": "1.0",
        "source": {
            "file_name": path.name,
            "file_hash": _compute_file_hash(path),
            "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "patterns": patterns,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_catalog(
    workspace: "WorkspaceContext",
    client: "LLMClient",
    catalog_dir: Path,
    force: bool = False,
) -> None:
    """Catalog all template PPTX files in *workspace*, writing to *catalog_dir*."""
    catalog_dir.mkdir(parents=True, exist_ok=True)

    candidates = [ti.path for ti in workspace.templates if ti.path.suffix.lower() == _PPTX_EXT]

    if not candidates:
        print("No PPTX template files found to catalog.")
        return

    print(f"Scanning {len(candidates)} template(s)...")

    for i, path in enumerate(candidates, 1):
        catalog_path = catalog_dir / (path.stem + ".catalog.json")
        prefix = f"[{i}/{len(candidates)}] {path.name}"

        if not force:
            file_hash = _compute_file_hash(path)
            if _is_current(catalog_path, file_hash):
                print(f"{prefix} -- unchanged, skipping.")
                continue

        print(f"{prefix} -> cataloging...")
        try:
            data = extract_catalog(path, client)
        except Exception as exc:
            print(f"  Error: {exc}")
            continue

        catalog_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  Saved: {catalog_path.name}")

    print("Done.")
