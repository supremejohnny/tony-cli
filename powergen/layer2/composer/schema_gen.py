"""Auto-generate a schema dict from a pptx by local shape extraction.

Schema version 2 additions vs v1:
- GROUP shapes: sub-shapes recursively flattened into slide slots
- TABLE shapes: extracted as kind="table" with 2D list defaults
- Layout metadata per slot: top_pct, left_pct, width_pct, height_pct, font_size_pt, font_name
- visual_only flag per slot: decorative font detection (Wingdings-family or Latin-Extended ratio)
- Slide-level decorative_heavy flag with _meta stats
"""
from __future__ import annotations

import json
from pathlib import Path

_DECORATIVE_FONTS = frozenset({
    "wingdings", "wingdings 2", "wingdings 3", "webdings", "symbol",
    "marlett", "segoe ui symbol",
})


def _is_visual_only(font_name: str | None, text: str) -> bool:
    if font_name and font_name.lower() in _DECORATIVE_FONTS:
        return True
    if text:
        latin_ext = sum(1 for c in text if "Ā" <= c <= "ɏ")
        if latin_ext / max(len(text), 1) > 0.15:
            return True
    return False


def _get_font_info(shape) -> tuple[str | None, int | None]:
    """Return (font_name, font_size_pt) from first run of first paragraph."""
    try:
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                sz = run.font.size
                name = run.font.name
                return name, (int(sz / 12700) if sz else None)
    except Exception:
        pass
    return None, None


def _layout_meta(shape, slide_w: int, slide_h: int) -> dict:
    try:
        return {
            "top_pct": round(shape.top / slide_h, 4),
            "left_pct": round(shape.left / slide_w, 4),
            "width_pct": round(shape.width / slide_w, 4),
            "height_pct": round(shape.height / slide_h, 4),
        }
    except Exception:
        return {}


def _iter_shapes(shapes):
    """Yield all shapes recursively, flattening GROUP containers."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _iter_shapes(shape.shapes)
        else:
            yield shape


def _count_names(shapes) -> dict[str, int]:
    counts: dict[str, int] = {}
    for shape in _iter_shapes(shapes):
        if shape.has_table:
            if any(
                cell.text_frame.text.strip()
                for row in shape.table.rows
                for cell in row.cells
            ):
                counts[shape.name] = counts.get(shape.name, 0) + 1
        elif shape.has_text_frame and shape.text_frame.text.strip():
            counts[shape.name] = counts.get(shape.name, 0) + 1
    return counts


def generate(pptx_path: Path) -> dict:
    from pptx import Presentation

    prs = Presentation(str(pptx_path))
    slide_w = prs.slide_width
    slide_h = prs.slide_height
    reusable_slides: dict = {}

    for i, slide in enumerate(prs.slides):
        total_count = _count_names(slide.shapes)
        slots: dict = {}
        occurrence: dict[str, int] = {}
        word_counts: list[int] = []  # for decorative_heavy calc (text shapes only)

        for shape in _iter_shapes(slide.shapes):
            sname = shape.name

            # --- TABLE ---
            if shape.has_table:
                rows_data: list[list[str]] = []
                has_text = False
                for row in shape.table.rows:
                    row_data = []
                    for cell in row.cells:
                        ct = cell.text_frame.text.strip()
                        row_data.append(ct)
                        if ct:
                            has_text = True
                    rows_data.append(row_data)
                if not has_text:
                    continue

                n = occurrence.get(sname, 0)
                occurrence[sname] = n + 1
                slot_key = sname if n == 0 else f"{sname}_{n}"

                slot: dict = {
                    "kind": "table",
                    "shape_name": sname,
                    "required": True,
                    "default": rows_data,
                }
                if total_count.get(sname, 0) > 1:
                    slot["nth"] = n
                slot.update(_layout_meta(shape, slide_w, slide_h))
                slots[slot_key] = slot
                continue

            # --- TEXT FRAME ---
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            if not text:
                continue

            font_name, font_size = _get_font_info(shape)
            visual_only = _is_visual_only(font_name, text)

            n = occurrence.get(sname, 0)
            occurrence[sname] = n + 1
            slot_key = sname if n == 0 else f"{sname}_{n}"

            paras_with_text = [p for p in shape.text_frame.paragraphs if p.text.strip()]
            kind = "multiline" if len(paras_with_text) > 1 else "text"

            slot = {
                "kind": kind,
                "shape_name": sname,
                "required": True,
                "default": text[:120],
            }
            if visual_only:
                slot["visual_only"] = True
            if total_count.get(sname, 0) > 1:
                slot["nth"] = n
            slot.update(_layout_meta(shape, slide_w, slide_h))
            if font_name:
                slot["font_name"] = font_name
            if font_size:
                slot["font_size_pt"] = font_size
            slots[slot_key] = slot

            word_counts.append((len(text.split()), len(text)))

        if not slots:
            continue

        # Decorative-heavy detection
        # avg_chars < 12 avoids Chinese text false positives (Chinese sentences have no spaces but many chars)
        # "short" shape = few words AND few chars (e.g. "01", "logo")
        n_text = len(word_counts)
        avg_chars = sum(c for _, c in word_counts) / max(n_text, 1)
        short_count = sum(1 for w, c in word_counts if w <= 3 and c <= 8)
        short_ratio = short_count / max(n_text, 1)
        decorative_heavy = (n_text > 10 and avg_chars < 12) or (n_text > 6 and short_ratio > 0.7)

        layout_name = ""
        try:
            layout_name = slide.slide_layout.name
        except Exception:
            pass

        purpose = f"Slide {i + 1}"
        if layout_name:
            purpose += f" — {layout_name}"

        slide_meta: dict = {
            "source_slide_index": i,
            "purpose": purpose,
            "reuse_tier": "template_local",
            "slots": slots,
        }
        if decorative_heavy:
            slide_meta["decorative_heavy"] = True
            slide_meta["_meta"] = {
                "text_shape_count": n_text,
                "avg_chars_per_shape": round(avg_chars, 2),
                "short_shape_ratio": round(short_ratio, 2),
                "short_def": "word_count<=3 AND char_count<=8",
            }

        reusable_slides[f"slide_{i}"] = slide_meta

    return {
        "schema_version": "2",
        "template_id": f"auto:{pptx_path.stem}",
        "source_pptx": pptx_path.name,
        "tokens": {},
        "reusable_slides": reusable_slides,
        "generated_slides": {},
        "compose_hints": {
            "ordering_rule": (
                "Select slides that best fit the topic and structure. "
                "You may reuse any slide multiple times with different content. "
                "Use each slot's default value to understand the slide's original purpose. "
                "For slides marked decorative_heavy=true, use fill: {}."
            )
        },
    }


def load_or_generate(pptx_path: Path) -> tuple[dict, Path]:
    """Return (schema, schema_path). Regenerate if schema_version < 2."""
    pptx_path = pptx_path.resolve()
    cache_path = pptx_path.with_suffix(".schema.json")

    if cache_path.exists():
        schema = json.loads(cache_path.read_text(encoding="utf-8"))
        if schema.get("schema_version", "1") >= "2":
            n = len(schema.get("reusable_slides", {}))
            print(f"Schema: loaded cache — {n} slides ({cache_path.name})")
            return schema, cache_path
        print("Schema: v1 cache found, regenerating with v2 features…")

    schema = generate(pptx_path)
    cache_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    n = len(schema["reusable_slides"])
    print(f"Schema: auto-generated {n} slides → {cache_path.name}")
    return schema, cache_path
