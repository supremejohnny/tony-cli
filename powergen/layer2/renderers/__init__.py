from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def render_generated(prs, entry: dict):
    """Dispatch a 'type: generated' plan entry to the appropriate renderer.
    Returns the new slide, or None if the content_type is unsupported.
    """
    content_type = entry.get("content_type", "bullet")
    if content_type == "bullet":
        from .bullet import render_bullet
        return render_bullet(prs, entry)
    print(f"  Warning: unsupported content_type '{content_type}', skipping.")
    return None
