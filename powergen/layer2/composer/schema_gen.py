"""
Auto-generate a schema dict from a pptx by local shape extraction.

No LLM call — purely structural: every text-bearing shape on every
slide becomes a named slot. The Composer LLM receives each slot's
existing text as a default so it can infer purpose from context.
"""
from __future__ import annotations

import json
from pathlib import Path


def generate(pptx_path: Path) -> dict:
    from pptx import Presentation

    prs = Presentation(str(pptx_path))
    reusable_slides: dict = {}

    for i, slide in enumerate(prs.slides):
        slots: dict = {}
        name_count: dict[str, int] = {}

        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            text = shape.text_frame.text.strip()
            if not text:
                continue

            sname = shape.name
            n = name_count.get(sname, 0)
            name_count[sname] = n + 1

            paras_with_text = [p for p in shape.text_frame.paragraphs if p.text.strip()]
            kind = "multiline" if len(paras_with_text) > 1 else "text"

            slot_key = sname if n == 0 else f"{sname}_{n}"
            slot: dict = {
                "kind": kind,
                "shape_name": sname,
                "required": True,
                "default": text[:120],
            }
            if n > 0:
                slot["nth"] = n
            slots[slot_key] = slot

        if not slots:
            continue

        layout_name = ""
        try:
            layout_name = slide.slide_layout.name
        except Exception:
            pass

        purpose = f"Slide {i + 1}"
        if layout_name:
            purpose += f" — {layout_name}"

        reusable_slides[f"slide_{i}"] = {
            "source_slide_index": i,
            "purpose": purpose,
            "reuse_tier": "template_local",
            "slots": slots,
        }

    return {
        "schema_version": "1",
        "template_id": f"auto:{pptx_path.stem}",
        "source_pptx": pptx_path.name,
        "tokens": {},
        "reusable_slides": reusable_slides,
        "generated_slides": {},
        "compose_hints": {
            "ordering_rule": (
                "Select slides that best fit the topic and structure. "
                "You may reuse any slide multiple times with different content. "
                "Use each slot's default value to understand the slide's original purpose."
            )
        },
    }


def load_or_generate(pptx_path: Path) -> tuple[dict, Path]:
    """Return (schema, schema_path). Generate + cache if not already cached."""
    pptx_path = pptx_path.resolve()
    cache_path = pptx_path.with_suffix(".schema.json")

    if cache_path.exists():
        schema = json.loads(cache_path.read_text(encoding="utf-8"))
        n = len(schema.get("reusable_slides", {}))
        print(f"Schema: loaded cache — {n} slides ({cache_path.name})")
        return schema, cache_path

    schema = generate(pptx_path)
    cache_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    n = len(schema["reusable_slides"])
    print(f"Schema: auto-generated {n} slides → {cache_path.name}")
    return schema, cache_path
