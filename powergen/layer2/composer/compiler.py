"""Call 2: deterministic spec IR → plan.json. No LLM calls.

Maps each spec item to a reusable slide (intent_tags match) or a generated slide (fallback).
Slot filling uses slot_label (from annotator) or inferred_label (from schema_gen v4).
"""
from __future__ import annotations

# Spec intent → generated structure_type when no reusable slide matches
_INTENT_TO_STRUCTURE_TYPE: dict[str, str] = {
    "cover":      "section",
    "section":    "section",
    "list":       "list",
    "comparison": "comparison",
    "process":    "process",
    "group":      "cards",
    "highlight":  "list",
    "closing":    "section",
}

# Primary intent not in template → try these fallback intents before going generated
_INTENT_FALLBACK: dict[str, list[str]] = {
    "highlight": ["list"],
    "closing":   ["section"],
}


def compile_plan(spec: dict, schema: dict) -> dict:
    """Map spec items to plan slides using intent_tags from schema."""
    reusable = schema.get("reusable_slides", {})
    intent_index = _build_intent_index(reusable)
    usage: dict[str, int] = {}

    slides = []
    for item in spec.get("slides", []):
        intent = item.get("intent", "list")
        key = _pick_reusable(intent, intent_index, reusable, usage)

        if key:
            fill = _fill_reusable(item, reusable[key])
            slides.append({"type": "reusable", "key": key, "fill": fill})
        else:
            st = _INTENT_TO_STRUCTURE_TYPE.get(intent, "list")
            fill = _fill_generated(item, st)
            slides.append({"type": "generated", "structure_type": st, "fill": fill})

    return {"title": spec.get("title", ""), "slides": slides}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_intent_index(reusable: dict) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for key, sdef in reusable.items():
        for tag in sdef.get("intent_tags", []):
            index.setdefault(tag, []).append(key)
    return index


def _pick_reusable(
    intent: str,
    intent_index: dict[str, list[str]],
    reusable: dict,
    usage: dict[str, int],
) -> str | None:
    """Return the least-used eligible reusable slide key, or None."""
    def candidates_for(tag: str) -> list[str]:
        return [
            k for k in intent_index.get(tag, [])
            if reusable[k].get("composable", True)
            and not reusable[k].get("decorative_heavy", False)
        ]

    pool = candidates_for(intent)
    if not pool:
        for fallback in _INTENT_FALLBACK.get(intent, []):
            pool = candidates_for(fallback)
            if pool:
                break

    if not pool:
        return None

    key = min(pool, key=lambda k: usage.get(k, 0))
    usage[key] = usage.get(key, 0) + 1
    return key


def _get_label_map(slide_def: dict) -> dict[str, list[str]]:
    """Build label → [slot_key] from slot_label (annotator) or inferred_label (schema_gen).
    Table slots are excluded — they are filled by the table-specific pass in _fill_reusable."""
    label_map: dict[str, list[str]] = {}
    for k, v in slide_def.get("slots", {}).items():
        if v.get("visual_only") or v.get("kind") == "table":
            continue
        label = v.get("slot_label") or v.get("inferred_label")
        if label:
            label_map.setdefault(label, []).append(k)
    return label_map


def _put(fill: dict, label_map: dict[str, list[str]], label: str, value) -> None:
    if value is None:
        return
    slots = label_map.get(label, [])
    if slots:
        fill[slots[0]] = value


def _fill_reusable(spec_item: dict, slide_def: dict) -> dict:
    """Normalize spec item fields → {slot_key: value} using label mapping."""
    fill: dict = {}
    intent = spec_item.get("intent", "")
    lm = _get_label_map(slide_def)

    # Content-heavy intents use subtitle slot as body fallback (annotator sometimes labels
    # the main text area as "subtitle" when it's actually the content zone)
    if intent in ("list", "process", "highlight", "comparison", "group", "closing"):
        if "body" not in lm and "subtitle" in lm:
            lm = dict(lm)
            lm["body"] = lm["subtitle"]

    _put(fill, lm, "title", spec_item.get("title"))
    _put(fill, lm, "subtitle", spec_item.get("subtitle"))

    if intent == "list":
        items = spec_item.get("items", [])
        _put(fill, lm, "body", "\n".join(f"• {x}" for x in items))

    elif intent == "process":
        steps = spec_item.get("steps", [])
        _put(fill, lm, "body", "\n".join(f"{i + 1}. {x}" for i, x in enumerate(steps)))

    elif intent == "comparison":
        pairs = spec_item.get("pairs", [])
        lines = []
        for p in pairs:
            left, right = p.get("left", {}), p.get("right", {})
            lines.append(f"{left.get('heading', '')}: {left.get('body', '')}")
            lines.append(f"{right.get('heading', '')}: {right.get('body', '')}")
        _put(fill, lm, "body", "\n".join(lines))

    elif intent == "group":
        cards = spec_item.get("cards", [])
        lines = [f"{c.get('heading', '')}: {c.get('body', '')}" for c in cards]
        _put(fill, lm, "body", "\n".join(lines))

    elif intent == "highlight":
        _put(fill, lm, "body", spec_item.get("body"))

    elif intent == "closing":
        _put(fill, lm, "body", spec_item.get("body"))

    # Table slots have no label → fill them directly from list-like spec content
    for slot_key, slot_def in slide_def.get("slots", {}).items():
        if slot_def.get("kind") != "table" or slot_key in fill:
            continue
        if intent == "list":
            items = spec_item.get("items", [])
            if items:
                fill[slot_key] = [[item] for item in items]
        elif intent == "process":
            steps = spec_item.get("steps", [])
            if steps:
                fill[slot_key] = [[f"{i + 1}. {s}"] for i, s in enumerate(steps)]
        elif intent in ("group", "comparison"):
            cards = spec_item.get("cards") or []
            pairs = spec_item.get("pairs") or []
            rows = []
            for c in cards:
                rows.append([f"{c.get('heading','')}: {c.get('body','')}"])
            for p in pairs:
                rows.append([p.get("left", {}).get("heading", ""), p.get("right", {}).get("heading", "")])
            if rows:
                fill[slot_key] = rows

    return fill


def _fill_generated(spec_item: dict, structure_type: str) -> dict:
    """Normalize spec item into generated slide fill format."""
    intent = spec_item.get("intent", "")
    title = spec_item.get("title", "")

    if structure_type == "section":
        return {
            "title": title,
            "subtitle": spec_item.get("subtitle") or spec_item.get("body") or "",
        }

    if structure_type == "list":
        items = spec_item.get("items", [])
        if not items and spec_item.get("body"):
            items = [spec_item["body"]]
        return {"title": title, "items": items}

    if structure_type == "comparison":
        pairs = spec_item.get("pairs", [])
        items = []
        for p in pairs:
            items.append({"heading": p.get("left", {}).get("heading", ""),
                          "body":    p.get("left", {}).get("body", "")})
            items.append({"heading": p.get("right", {}).get("heading", ""),
                          "body":    p.get("right", {}).get("body", "")})
        return {"title": title, "items": items[:2]}

    if structure_type == "cards":
        return {"title": title, "items": spec_item.get("cards", [])}

    if structure_type == "process":
        return {"title": title, "items": spec_item.get("steps", [])}

    return {"title": title}
