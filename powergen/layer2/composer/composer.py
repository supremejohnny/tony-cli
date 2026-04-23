"""
Composer: execute a plan dict against a schema, producing a Presentation.

For each plan slide:
  - type "reusable"  → clone_and_fill from source pptx
  - type "generated" → call the registered renderer with fill + tokens
"""
import io

from pptx import Presentation

from .renderers import get as get_renderer
from .slide_cloner import clone_and_fill


def compose(schema: dict, src_prs: Presentation, plan: dict) -> Presentation:
    """
    Build an output Presentation by executing plan against schema.

    Args:
        schema:   loaded + comment-stripped schema dict
        src_prs:  source Presentation (template .pptx)
        plan:     {"title": str, "slides": [...]}

    Returns:
        A new Presentation with all slides appended.
    """
    buf = io.BytesIO()
    src_prs.save(buf)
    buf.seek(0)
    dest_prs = Presentation(buf)
    _clear_slides(dest_prs)

    tokens = schema.get("tokens", {})
    reusable = schema.get("reusable_slides", {})

    for entry in plan.get("slides", []):
        slide_type = entry.get("type")
        fill = entry.get("fill", {})

        if slide_type == "reusable":
            key = entry.get("key")
            if key not in reusable:
                raise ValueError(f"Unknown reusable slide key {key!r}. Available: {list(reusable)}")
            clone_and_fill(src_prs, dest_prs, reusable[key], fill)

        elif slide_type == "generated":
            content_type = entry.get("content_type")
            render = get_renderer(content_type)
            render(dest_prs, fill, tokens)

        else:
            raise ValueError(f"Unknown slide type {slide_type!r} — expected 'reusable' or 'generated'")

    return dest_prs


def _clear_slides(prs: Presentation) -> None:
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT
    prs_part = prs.part
    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst):
        sldIdLst.remove(sldId)
    slide_rids = [
        rId for rId, rel in list(prs_part.rels.items())
        if not rel.is_external and rel.reltype == RT.SLIDE
    ]
    for rId in slide_rids:
        prs_part.drop_rel(rId)
