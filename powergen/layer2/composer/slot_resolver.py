"""
Resolve slot locators (shape_name / nth / near) to python-pptx shapes.

Strategy in order of preference (from SKILL.md):
  1. shape_name only — when the name is unique on the slide
  2. shape_name + nth — Nth occurrence (0-indexed, document order)
  3. shape_name + near {top, left} — closest by Manhattan distance in inches
"""
from pptx.util import Emu


def _to_in(emu):
    return Emu(emu).inches if emu is not None else 0.0


def resolve(slide, shape_name, nth=None, near=None):
    """
    Return the single shape matching the locator, or raise ValueError.

    Args:
        slide: pptx.slide.Slide
        shape_name: exact shape name string
        nth: 0-indexed occurrence when name repeats (optional)
        near: {"top": float, "left": float} in inches — pick closest (optional)

    Raises:
        ValueError if the locator is ambiguous or resolves to zero shapes.
    """
    candidates = [s for s in slide.shapes if s.name == shape_name]
    if not candidates:
        raise ValueError(f"No shape named {shape_name!r} on slide")

    if nth is not None:
        if not (0 <= nth < len(candidates)):
            raise ValueError(
                f"nth={nth} out of range — {len(candidates)} shapes named {shape_name!r}"
            )
        return candidates[nth]

    if near is not None:
        t0, l0 = near.get("top", 0.0), near.get("left", 0.0)
        return min(
            candidates,
            key=lambda s: abs(_to_in(s.top) - t0) + abs(_to_in(s.left) - l0),
        )

    if len(candidates) > 1:
        raise ValueError(
            f"Ambiguous: {len(candidates)} shapes named {shape_name!r} — add nth or near"
        )
    return candidates[0]


def resolve_slot(slide, slot_def):
    """
    Resolve a non-repeating slot definition dict to a shape.
    slot_def must contain 'shape_name'; optionally 'nth' and/or 'near'.
    """
    return resolve(
        slide,
        slot_def["shape_name"],
        nth=slot_def.get("nth"),
        near=slot_def.get("near"),
    )


def resolve_repeating_field(slide, field_def, instance_index, stride_x=0.0, stride_y=0.0):
    """
    Resolve one field within a repeating slot at position instance_index.

    Finds all shapes named field_def["shape_name"], then selects the one
    whose position is closest to (base + index * stride).

    Returns the matching shape, or raises ValueError.
    """
    shape_name = field_def["shape_name"]
    candidates = [s for s in slide.shapes if s.name == shape_name]
    if not candidates:
        raise ValueError(f"No shape named {shape_name!r} on slide (repeating field)")

    base = min(candidates, key=lambda s: (_to_in(s.top), _to_in(s.left)))
    target_top = _to_in(base.top) + instance_index * stride_y
    target_left = _to_in(base.left) + instance_index * stride_x

    return min(
        candidates,
        key=lambda s: abs(_to_in(s.top) - target_top) + abs(_to_in(s.left) - target_left),
    )
