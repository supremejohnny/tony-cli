from __future__ import annotations

from pathlib import Path


def generate(pptx_path: Path) -> dict:
    """Extract slide inventory from a .pptx file. Pure code, zero LLM tokens.

    Duplicate shape names within a slide are suffixed with [0], [1], … so the
    LLM can target each occurrence individually via text_map keys.
    """
    from pptx import Presentation  # type: ignore[import]

    prs = Presentation(str(pptx_path))
    slides = []
    for i, slide in enumerate(prs.slides):
        raw: list[dict] = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            if text:
                raw.append({"name": shape.name, "text": text[:120]})

        # Count occurrences per name to detect duplicates
        counts: dict[str, int] = {}
        for s in raw:
            counts[s["name"]] = counts.get(s["name"], 0) + 1

        # Assign indexed display names for shapes whose name appears > 1 time
        seen: dict[str, int] = {}
        shapes: list[dict] = []
        for s in raw:
            base = s["name"]
            if counts[base] > 1:
                idx = seen.get(base, 0)
                seen[base] = idx + 1
                display = f"{base}[{idx}]"
            else:
                display = base
            shapes.append({"name": display, "text": s["text"]})

        slides.append({
            "index": i,
            "layout": slide.slide_layout.name,
            "shapes": shapes,
        })
    return {"slides": slides}


def format_for_prompt(inventory: dict) -> str:
    """Render inventory as a compact text block suitable for an LLM prompt."""
    lines: list[str] = []
    for slide in inventory["slides"]:
        lines.append(f"\n--- Slide {slide['index']} | layout: {slide['layout']!r} ---")
        if not slide["shapes"]:
            lines.append("  (no text shapes)")
            continue
        for shape in slide["shapes"]:
            preview = shape["text"].replace("\n", " | ")
            lines.append(f'  "{shape["name"]}": "{preview}"')
    return "\n".join(lines)
