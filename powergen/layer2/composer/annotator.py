"""LLM-powered schema annotator.

Reads a v4 schema and produces per-slide semantic annotations:
  - composable flag (false only for decorative_heavy)
  - intent_tags: closed-set list from 8 intent types
  - slot-level semantic label from role whitelist + confidence

Annotations cached as <stem>.annotated.json.
Annotator v1 → v2: added intent_tags output.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_ANNOTATOR_VERSION = "2"

_ROLE_WHITELIST = frozenset({"title", "subtitle", "body", "label", "caption", "callout"})
_UNIQUE_ROLES = frozenset({"title", "subtitle"})
_INTENT_WHITELIST = frozenset({
    "cover", "section", "list", "comparison", "process", "group", "highlight", "closing"
})

_SYSTEM_PROMPT = """\
You are a presentation template analyst. Annotate each slide in the schema.

For EACH slide output:

1. composable: true or false
   → false ONLY if the slide has decorative_heavy=true
   → true for ALL other slides, even if text looks garbled

2. intent_tags: list of 0–2 values from this CLOSED SET:
     cover       — title slide (large dominant title, typically first slide)
     section     — chapter divider (large title + optional small subtitle, NO bullet body)
     list        — title + body area for multiple bullet points (body slot must have real vertical space)
     comparison  — two parallel content columns
     process     — sequential steps or flow layout
     group       — grid of equal-weight card items
     highlight   — single key fact (title + one short body)
     closing     — end-of-presentation slide (typically last)
   Use [] for decorative_heavy slides or slides with no clear content role.

   Distinguish section vs list carefully:
   - section: the body area is SMALL or absent — the slide is a visual divider, not a content container
   - list: the body area is LARGE enough for bullet points (height_pct > 0.25, or multiline kind)

   A schema hint from layout-name inference is shown — confirm or override based on visual evidence.
   Max 2 tags per slide.

3. slots: annotate each non-visual_only slot:
   label: ONE of: title, subtitle, body, label, caption, callout
   confidence: high | medium | low

Hard rules:
- Only one "title" per slide, only one "subtitle" per slide
- At most 3 "high" confidence labels per slide
- Skip slots marked visual_only=true

Output ONLY valid JSON, no markdown fences, no explanation.

Format:
{
  "slides": {
    "slide_0": {
      "composable": true,
      "intent_tags": ["cover"],
      "slots": {
        "Title 2": {"label": "title", "confidence": "high"},
        "Subtitle 3": {"label": "subtitle", "confidence": "high"}
      }
    },
    "slide_1": {
      "composable": true,
      "intent_tags": ["section"],
      "slots": {
        "文本框 5": {"label": "title", "confidence": "high"}
      }
    },
    "slide_2": {
      "composable": true,
      "intent_tags": ["list"],
      "slots": {
        "文本框 10": {"label": "title", "confidence": "high"},
        "文本框 1": {"label": "body", "confidence": "high"}
      }
    },
    "slide_3": {
      "composable": false,
      "intent_tags": [],
      "slots": {}
    }
  }
}
"""


def annotate(schema: dict, client) -> dict:
    user_prompt = _build_prompt(schema)
    raw = client.generate(_SYSTEM_PROMPT, user_prompt)
    annotations = _parse_json(raw)
    annotations["annotator_version"] = _ANNOTATOR_VERSION
    return _post_process(annotations, schema)


def load_or_annotate(schema: dict, schema_path: Path, client) -> dict:
    ann_path = _ann_path(schema_path)

    if ann_path.exists():
        annotations = json.loads(ann_path.read_text(encoding="utf-8"))
        if annotations.get("annotator_version", "1") >= _ANNOTATOR_VERSION:
            print(f"Annotator: loaded cache ({ann_path.name})")
            return annotations
        print("Annotator: cache is v1, re-annotating for intent_tags…")

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

        # Annotator intent_tags override schema_gen inference (has more context)
        if "intent_tags" in ann_slide:
            slide_def["intent_tags"] = ann_slide["intent_tags"]

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
    stem = schema_path.stem
    if stem.endswith(".schema"):
        stem = stem[:-7]
    return schema_path.parent / f"{stem}.annotated.json"


def _build_prompt(schema: dict) -> str:
    lines = [f"Template: {schema.get('template_id', 'unknown')}\n"]

    for slide_key, sdef in schema.get("reusable_slides", {}).items():
        decorative = sdef.get("decorative_heavy", False)
        meta = sdef.get("_meta", {})
        schema_hint = sdef.get("intent_tags", [])

        header = f"[{slide_key}] {sdef.get('purpose', '')}"
        if schema_hint:
            header += f"  [schema hint: {schema_hint}]"
        if decorative:
            header += (
                f"  <<decorative_heavy: text_shapes={meta.get('text_shape_count')}, "
                f"avg_chars={meta.get('avg_chars_per_shape')}>>"
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
                pos = f" pos=({slot_def['top_pct']:.2f}t,{slot_def['left_pct']:.2f}l,h={slot_def.get('height_pct',0):.2f})"

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
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    cleaned = re.sub(r",\s*([}\]])", r"\1", raw)
    return json.loads(cleaned)


def _post_process(annotations: dict, schema: dict) -> dict:
    for slide_key, ann_slide in annotations.get("slides", {}).items():
        slide_def = schema.get("reusable_slides", {}).get(slide_key, {})

        # composable override
        if not ann_slide.get("composable", True) and not slide_def.get("decorative_heavy", False):
            ann_slide["composable"] = True

        # intent_tags: enforce closed-set whitelist, max 2
        raw_tags = ann_slide.get("intent_tags", [])
        ann_slide["intent_tags"] = [t for t in raw_tags if t in _INTENT_WHITELIST][:2]

        if not ann_slide.get("composable", True):
            ann_slide["intent_tags"] = []
            ann_slide["slots"] = {}
            continue

        # slot labels
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
