from __future__ import annotations

import copy
from io import BytesIO
from pathlib import Path


def compose(template_path: Path, plan: dict, output_path: Path) -> Path:
    """Clone slides from template per plan, fill text_map, save to output_path."""
    from pptx import Presentation  # type: ignore[import]

    src_prs = Presentation(str(template_path))

    # Initialise dest from a copy of src so master/layouts/theme are preserved
    buf = BytesIO()
    src_prs.save(buf)
    buf.seek(0)
    dest_prs = Presentation(buf)
    _clear_slides(dest_prs)

    n_src = len(src_prs.slides)
    filled_count = 0
    skipped_count = 0

    for entry in plan.get("slides", []):
        if entry.get("type") == "generated":
            print(f"  [generated fallback not yet implemented, skipping]")
            skipped_count += 1
            continue

        idx = entry.get("source_slide_index", 0)
        if idx >= n_src:
            print(f"  Warning: source_slide_index {idx} out of range ({n_src} slides), skipping.")
            skipped_count += 1
            continue

        text_map: dict[str, str] = entry.get("text_map", {})
        slide = _clone_slide(src_prs, idx, dest_prs)
        _fill_slide(slide, text_map)
        filled_count += 1

    dest_prs.save(str(output_path))
    print(f"  Composed {filled_count} slides" + (f" ({skipped_count} skipped)" if skipped_count else ""))
    return output_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clear_slides(prs) -> None:
    from pptx.oxml.ns import qn  # type: ignore[import]

    sld_id_lst = prs.slides._sldIdLst
    for sld_id in list(sld_id_lst):
        r_id = sld_id.get(qn("r:id"))
        sld_id_lst.remove(sld_id)
        if r_id:
            try:
                prs.part.drop_rel(r_id)
            except Exception:
                pass


def _find_layout(prs, layout_name: str):
    for layout in prs.slide_layouts:
        if layout.name == layout_name:
            return layout
    return prs.slide_layouts[0]


def _clone_slide(src_prs, src_idx: int, dest_prs):
    """Clone a slide by matching layout + copying the shape tree."""
    src_slide = src_prs.slides[src_idx]
    layout = _find_layout(dest_prs, src_slide.slide_layout.name)
    new_slide = dest_prs.slides.add_slide(layout)

    sp_tree = new_slide.shapes._spTree
    for el in list(sp_tree):
        sp_tree.remove(el)
    for el in src_slide.shapes._spTree:
        sp_tree.append(copy.deepcopy(el))

    return new_slide


def _fill_slide(slide, text_map: dict[str, str]) -> None:
    """Best-effort: replace text in the first shape matching each name."""
    filled: set[str] = set()
    for shape in slide.shapes:
        name = shape.name
        if name in text_map and shape.has_text_frame and name not in filled:
            _replace_text(shape, text_map[name])
            filled.add(name)

    missing = sorted(set(text_map) - filled)
    for name in missing:
        print(f"    Warning: shape '{name}' not found, skipping.")


def _replace_text(shape, new_text: str) -> None:
    """Replace all text in a shape's text frame, preserving first-run formatting."""
    tf = shape.text_frame
    if not tf.paragraphs:
        return

    first_para = tf.paragraphs[0]
    if first_para.runs:
        first_para.runs[0].text = new_text
        for run in first_para.runs[1:]:
            run.text = ""
    else:
        first_para.text = new_text

    for para in tf.paragraphs[1:]:
        for run in para.runs:
            run.text = ""
