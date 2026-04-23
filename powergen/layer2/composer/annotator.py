"""LLM-powered schema annotator.

Reads a v2 schema and produces semantic annotations:
  - slide-level composable flag (False for decorative_heavy slides)
  - slot-level semantic label from role whitelist
  - confidence level: high / medium / low

Annotations cached as <stem>.annotated.json alongside the schema.
Run once per template; re-run by deleting the cache file.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_ROLE_WHITELIST = frozenset({"title", "subtitle", "body", "label", "caption", "callout"})
_UNIQUE_ROLES = frozenset({"title", "subtitle"})

_SYSTEM_PROMPT = """\
You are a presentation template analyst. Given a schema of slide shapes, annotate each slide.

For EACH slide output:
  composable: true or false
    → false ONLY if the slide has decorative_heavy=true (explicitly marked in schema)
    → true for ALL other slides, even if some text looks garbled or unreadable
  slots: annotate each non-visual_only slot:
    label: ONE of: title, subtitle, body, label, caption, callout
    confidence: high | medium | low
      high   = position + content clearly indicate this role
      medium = reasonable inference
      low    = uncertain, OR default text is garbled/unreadable

Hard rules:
- composable: false ONLY for decorative_heavy slides. Garbled text alone does NOT make a slide non-composable.
- Only one "title" per slide, only one "subtitle" per slide
- At most 3 "high" confidence labels per slide
- Skip slots marked visual_only=true (omit them entirely from output)

Output ONLY valid JSON, no markdown fences, no explanation.

Format:
{
  "slides": {
    "slide_0": {"composable": false, "reason": "decorative_heavy", "slots": {}},
    "slide_1": {
      "composable": true,
      "slots": {
        "Title 2": {"label": "title", "confidence": "high"},
        "object 6": {"label": "caption", "confidence": "low"}
      }
    }
  }
}
"""


def annotate(schema: dict, client) -> dict:
    """Call LLM annotator and return post-processed annotations dict."""
    user_prompt = _build_prompt(schema)
    raw = client.generate(_SYSTEM_PROMPT, user_prompt)
    annotations = _parse_json(raw)
    return _post_process(annotations, schema)


def load_or_annotate(schema: dict, schema_path: Path, client) -> dict:
    """Return annotations, generating + caching if not found."""
    ann_path = _ann_path(schema_path)

    if ann_path.exists():
        annotations = json.loads(ann_path.read_text(encoding="utf-8"))
        print(f"Annotator: loaded cache ({ann_path.name})")
        return annotations

    print("Annotator: generating semantic annotations…")
    annotations = annotate(schema, client)
    ann_path.write_text(json.dumps(annotations, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Annotator: saved → {ann_path.name}")
    return annotations


def merge_into_schema(schema: dict, annotations: dict) -> dict:
    """Return a deep-copy of schema with annotation fields merged into slides/slots."""
    import copy
    schema = copy.deepcopy(schema)
    for slide_key, ann_slide in annotations.get("slides", {}).items():
        slide_def = schema.get("reusable_slides", {}).get(slide_key)
        if slide_def is None:
            continue
        if not ann_slide.get("composable", True):
            slide_def["composable"] = False
            slide_def["composable_reason"] = ann_slide.get("reason", "")
        for slot_key, slot_ann in ann_slide.get("slots", {}).items():
            slot_def = slide_def.get("slots", {}).get(slot_key)
            if slot_def is None:
                continue
            if slot_ann.get("label"):
                slot_def["slot_label"] = slot_ann["label"]
            if slot_ann.get("confidence"):
                slot_def["confidence"] = slot_ann["confidence"]
    return schema


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ann_path(schema_path: Path) -> Path:
    stem = schema_path.stem  # e.g. "courseplan_test.schema"
    if stem.endswith(".schema"):
        stem = stem[:-7]  # "courseplan_test"
    return schema_path.parent / f"{stem}.annotated.json"


def _build_prompt(schema: dict) -> str:
    lines = [f"Template: {schema.get('template_id', 'unknown')}\n"]

    for slide_key, sdef in schema.get("reusable_slides", {}).items():
        decorative = sdef.get("decorative_heavy", False)
        meta = sdef.get("_meta", {})

        header = f"[{slide_key}] {sdef.get('purpose', '')}"
        if decorative:
            header += (
                f"  <<decorative_heavy: text_shapes={meta.get('text_shape_count')}, "
                f"avg_words={meta.get('avg_words_per_shape')}>>"
            )
        lines.append(header)

        for slot_key, slot_def in sdef.get("slots", {}).items():
            if slot_def.get("visual_only"):
                lines.append(f"  - {slot_key}: [visual_only — skip]")
                continue

            kind = slot_def.get("kind", "text")
            default = slot_def.get("default", "")

            if kind == "table":
                first_row = default[0] if default else []
                preview = str(first_row)[:60]
            else:
                preview = str(default)[:60].replace("\n", " ").replace("\v", " ")

            pos = ""
            if "top_pct" in slot_def:
                pos = f" pos=({slot_def['top_pct']:.2f}t,{slot_def['left_pct']:.2f}l)"

            font = ""
            if "font_size_pt" in slot_def:
                font = f" {slot_def['font_size_pt']}pt"

            lines.append(f"  - {slot_key} ({kind}{pos}{font}): {preview!r}")

        lines.append("")

    lines.append("Annotate all slides above.")
    return "\n".join(lines)


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        raw = m.group(1).strip()
    return json.loads(raw)


def _post_process(annotations: dict, schema: dict) -> dict:
    """Enforce role whitelist, uniqueness, high-confidence count cap, and composable override."""
    for slide_key, ann_slide in annotations.get("slides", {}).items():
        # composable:false only valid when slide is decorative_heavy in the schema
        slide_def = schema.get("reusable_slides", {}).get(slide_key, {})
        if not ann_slide.get("composable", True) and not slide_def.get("decorative_heavy", False):
            ann_slide["composable"] = True  # override incorrect non-composable classification

        if not ann_slide.get("composable", True):
            ann_slide["slots"] = {}
            continue

        seen_unique: set[str] = set()
        high_count = 0
        valid_slots: dict = {}

        for slot_key, slot_ann in ann_slide.get("slots", {}).items():
            label = slot_ann.get("label", "")
            confidence = slot_ann.get("confidence", "low")

            if label not in _ROLE_WHITELIST:
                continue

            if label in _UNIQUE_ROLES and label in seen_unique:
                slot_ann["confidence"] = "low"
            if label in _UNIQUE_ROLES:
                seen_unique.add(label)

            if confidence == "high":
                if high_count >= 3:
                    slot_ann["confidence"] = "medium"
                else:
                    high_count += 1

            valid_slots[slot_key] = slot_ann

        ann_slide["slots"] = valid_slots

    return annotations
