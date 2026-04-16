"""
Load a template.schema.json and return a clean dict (underscore-prefixed comment fields stripped).
"""
import json
from pathlib import Path


def strip_comments(obj):
    """Recursively remove keys starting with '_' (doc-comment convention)."""
    if isinstance(obj, dict):
        return {k: strip_comments(v) for k, v in obj.items() if not k.startswith("_")}
    if isinstance(obj, list):
        return [strip_comments(v) for v in obj]
    return obj


def load(schema_path):
    """
    Load schema JSON from path, strip comment fields, return clean dict.

    Returns dict with: schema_version, template_id, source_pptx, tokens,
    reusable_slides, generated_slides, compose_hints.
    """
    path = Path(schema_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    return strip_comments(raw)


def source_pptx_path(schema, schema_path):
    """Resolve source_pptx path relative to the schema file."""
    return Path(schema_path).parent / schema["source_pptx"]
