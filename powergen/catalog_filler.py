from __future__ import annotations

import json
import shutil
from copy import deepcopy
from pathlib import Path

from pptx.oxml.ns import qn  # type: ignore[import]

from .catalog import load_catalog_slots


# ---------------------------------------------------------------------------
# Shape-level text writing
# ---------------------------------------------------------------------------

def _write_shape(shape, content: str, content_type: str) -> None:
    """Write *content* into *shape*'s text frame, preserving paragraph/run formatting.

    Strategy:
    - Save the first paragraph element and first run element as format templates.
    - Remove all existing <a:p> elements from the txBody.
    - Re-insert one <a:p> per output line, each containing one <a:r> cloned from
      the saved run template (keeps font, size, colour, bold, etc.).
    """
    if not shape.has_text_frame:
        return

    lines: list[str]
    if content_type == "bullets":
        lines = [l.strip() for l in content.split("\n") if l.strip()]
    else:
        lines = [content.strip()]

    if not lines:
        return

    txBody = shape.text_frame._txBody

    # --- save templates BEFORE touching the tree ---
    existing_paras = txBody.findall(qn("a:p"))
    tmpl_p = deepcopy(existing_paras[0]) if existing_paras else None
    tmpl_r: object | None = None
    if tmpl_p is not None:
        tmpl_rs = tmpl_p.findall(qn("a:r"))
        tmpl_r = deepcopy(tmpl_rs[0]) if tmpl_rs else None

    # --- remove all existing paragraphs ---
    for p in existing_paras:
        txBody.remove(p)

    # --- insert new paragraphs ---
    from lxml import etree  # type: ignore[import]

    for line in lines:
        # Build paragraph from template or scratch
        if tmpl_p is not None:
            new_p = deepcopy(tmpl_p)
            for r in new_p.findall(qn("a:r")):
                new_p.remove(r)
        else:
            new_p = etree.Element(qn("a:p"))

        # Build run from template or scratch
        if tmpl_r is not None:
            new_r = deepcopy(tmpl_r)
            t = new_r.find(qn("a:t"))
            if t is None:
                t = etree.SubElement(new_r, qn("a:t"))
        else:
            new_r = etree.Element(qn("a:r"))
            t = etree.SubElement(new_r, qn("a:t"))

        t.text = line
        new_p.append(new_r)
        txBody.append(new_p)


def _fill_slide(slide, slot_values: dict[str, str], slot_meta: dict[str, dict]) -> None:
    """Write all slot values into the matching shapes on *slide*.

    *slot_meta* maps slot_name → {shape_name, content_type, ...}.
    Shapes are matched by their exact ``shape.name`` attribute.
    """
    # Build lookup: shape_name → (content, content_type)
    targets: dict[str, tuple[str, str]] = {}
    for slot_name, content in slot_values.items():
        meta = slot_meta.get(slot_name)
        if meta is None:
            continue
        shape_name = meta.get("shape_name") or meta.get("name", "")
        content_type = meta.get("content_type", "text")
        if shape_name:
            targets[shape_name] = (content, content_type)

    filled: set[str] = set()
    for shape in slide.shapes:
        if shape.name in targets:
            content, content_type = targets[shape.name]
            _write_shape(shape, content, content_type)
            filled.add(shape.name)

    missing = set(targets) - filled
    if missing:
        for name in sorted(missing):
            print(f"  Warning: shape not found on slide: {name!r}")


# ---------------------------------------------------------------------------
# Slide ordering helpers  (python-pptx XML level)
# ---------------------------------------------------------------------------

def _reorder_slides(prs, ordered_indices: list[int]) -> None:
    """Reorder and prune slides so only *ordered_indices* (0-based) remain,
    in that order.  Slides not listed are dropped from the presentation.
    """
    sldIdLst = prs.slides._sldIdLst
    all_sldId = list(sldIdLst)          # snapshot before mutation
    n_original = len(all_sldId)

    # Remove all slide id entries
    for sid in all_sldId:
        sldIdLst.remove(sid)

    # Re-add only the ones we want, in plan order
    keep_set = set(ordered_indices)
    for idx in ordered_indices:
        sldIdLst.append(all_sldId[idx])

    # Drop package relationships for removed slides so pptx stays valid
    for idx in range(n_original):
        if idx not in keep_set:
            rId = all_sldId[idx].get(qn("r:id"))
            if rId:
                try:
                    prs.part.drop_rel(rId)
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def fill_from_plan(
    plan: list[dict],
    template_path: Path,
    catalog_path: Path,
    output_path: Path,
) -> Path:
    """Phase 3: Apply a content plan to a template PPTX and save to *output_path*.

    *plan* is the list returned by ``run_catalog_plan()``::

        [{"pattern_id": str, "slots": {slot_name: value, ...}}, ...]

    Each plan entry maps to a slide in the output.  When a pattern is used
    more than once only the first occurrence is filled (slide cloning is not
    yet supported); subsequent occurrences are silently skipped.

    Returns *output_path*.
    """
    from pptx import Presentation  # type: ignore[import]

    # --- load catalog data ---
    catalog_data = json.loads(catalog_path.read_text(encoding="utf-8"))
    pattern_to_src: dict[str, int] = {          # pattern_id → 0-based slide index
        p["pattern_id"]: p["source_slide"] - 1
        for p in catalog_data.get("patterns", [])
    }

    # --- load slot metadata for selected patterns ---
    pattern_ids = list({e["pattern_id"] for e in plan})
    slots_meta: dict[str, dict[str, dict]] = {
        p["pattern_id"]: {s["name"]: s for s in p.get("slots", [])}
        for p in load_catalog_slots(catalog_path, pattern_ids)
    }

    # --- work on a copy so the original template is never mutated ---
    shutil.copy2(str(template_path), str(output_path))
    prs = Presentation(str(output_path))
    n_slides = len(prs.slides)

    # --- build ordered list of source indices (deduplicated, first-use-wins) ---
    ordered_src: list[int] = []
    seen_src: set[int] = set()
    plan_work: list[tuple[int, dict]] = []          # (src_idx, plan_entry)

    for entry in plan:
        pid = entry.get("pattern_id", "")
        src = pattern_to_src.get(pid)
        if src is None:
            print(f"  Warning: pattern_id '{pid}' not found in catalog, skipping.")
            continue
        src = max(0, min(src, n_slides - 1))
        if src in seen_src:
            print(f"  Note: pattern '{pid}' already used (slide cloning not yet supported), skipping duplicate.")
            continue
        seen_src.add(src)
        ordered_src.append(src)
        plan_work.append((src, entry))

    # --- fill slots slide by slide ---
    for src_idx, entry in plan_work:
        slide = prs.slides[src_idx]
        pid = entry["pattern_id"]
        _fill_slide(slide, entry.get("slots", {}), slots_meta.get(pid, {}))

    # --- reorder / prune slides ---
    _reorder_slides(prs, ordered_src)

    prs.save(str(output_path))
    return output_path
