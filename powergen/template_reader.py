from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LayoutInfo:
    name: str
    index: int
    placeholder_names: list[str] = field(default_factory=list)


def read_template_layouts(pptx_path: Path) -> list[LayoutInfo]:
    """Return the slide layouts (name, index, placeholder names) from a .pptx template."""
    from pptx import Presentation  # type: ignore[import]
    from pptx.util import Pt  # noqa: F401 — imported to verify pptx is available

    prs = Presentation(str(pptx_path))
    layouts: list[LayoutInfo] = []
    for idx, layout in enumerate(prs.slide_layouts):
        ph_names = [ph.name for ph in layout.placeholders]
        layouts.append(LayoutInfo(name=layout.name, index=idx, placeholder_names=ph_names))
    return layouts
