from __future__ import annotations

from pathlib import Path


def generate(pptx_path: Path) -> dict:
    """Extract slide inventory from a .pptx file. Pure code, zero LLM tokens.

    Returns a dict with a "slides" list. Each slide entry contains:
      - index: 0-based slide index
      - layout: slide layout name
      - shapes: list of {name, text} for shapes that have non-empty text
    """
    from pptx import Presentation  # type: ignore[import]

    prs = Presentation(str(pptx_path))
    slides = []
    for i, slide in enumerate(prs.slides):
        shapes = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            if not text:
                continue
            shapes.append({
                "name": shape.name,
                "text": text[:120],
            })
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
