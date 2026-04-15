from __future__ import annotations

import zipfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS = {"a": _NS_A}


def _get_clr_value(el) -> str | None:
    """Extract hex color from a <a:dk1/lt1/accent1/…> element."""
    if el is None:
        return None
    from lxml import etree  # type: ignore[import]

    # Explicit sRGB value
    srgb = el.find("a:srgbClr", _NS)
    if srgb is not None:
        val = srgb.get("val", "")
        if len(val) == 6:
            return f"#{val.upper()}"

    # System color (carries lastClr as fallback)
    sys_clr = el.find("a:sysClr", _NS)
    if sys_clr is not None:
        last = sys_clr.get("lastClr", "")
        if len(last) == 6:
            return f"#{last.upper()}"

    return None


def _read_theme_xml(pptx_path: Path) -> bytes | None:
    """Return raw bytes of ppt/theme/theme1.xml (or the first theme file)."""
    try:
        with zipfile.ZipFile(str(pptx_path)) as z:
            # Prefer theme1.xml; fall back to first theme file found
            candidates = [
                n for n in z.namelist()
                if n.startswith("ppt/theme/") and n.endswith(".xml")
            ]
            if not candidates:
                return None
            name = next((c for c in candidates if "theme1" in c), candidates[0])
            return z.read(name)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract_theme_tokens(path: Path) -> dict:
    """Extract visual theme tokens directly from the PPTX theme XML.

    Reads *ppt/theme/theme*.xml* inside the ZIP — no heuristic shape scanning,
    so the values are accurate regardless of whether slides use explicit fills
    or inherited theme color references.

    Returns a dict with keys:
        bg_color      — '#RRGGBB'  (from dk2; dark background of branded templates)
        accent_color  — '#RRGGBB'  (from accent1)
        heading_font  — font family name for titles  (from majorFont)
        body_font     — font family name for body text (from minorFont)
    """
    # Defaults — classic PowerPoint blue-on-white in case extraction fails
    tokens = {
        "bg_color":     "#1B2A4A",
        "accent_color": "#2E75B6",
        "heading_font": "Calibri",
        "body_font":    "Calibri",
    }

    raw = _read_theme_xml(path)
    if not raw:
        return tokens

    try:
        from lxml import etree  # type: ignore[import]
        root = etree.fromstring(raw)

        # ── Color scheme ──────────────────────────────────────────────────
        clr_scheme = root.find(".//a:clrScheme", _NS)
        if clr_scheme is not None:
            # dk2 = branded dark background color (navy, slate, etc.)
            dk2 = _get_clr_value(clr_scheme.find("a:dk2", _NS))
            if dk2:
                tokens["bg_color"] = dk2

            # accent1 = primary highlight / brand color
            acc1 = _get_clr_value(clr_scheme.find("a:accent1", _NS))
            if acc1:
                tokens["accent_color"] = acc1

        # ── Font scheme ───────────────────────────────────────────────────
        font_scheme = root.find(".//a:fontScheme", _NS)
        if font_scheme is not None:
            def _latin_typeface(tag: str) -> str | None:
                el = font_scheme.find(f"{tag}/a:latin", _NS)
                if el is None:
                    return None
                tf = el.get("typeface", "")
                # Skip placeholder tokens like "+mj-lt" or "+mn-lt"
                return tf if (tf and not tf.startswith("+")) else None

            hf = _latin_typeface("a:majorFont")
            if hf:
                tokens["heading_font"] = hf

            bf = _latin_typeface("a:minorFont")
            if bf:
                tokens["body_font"] = bf

    except Exception:
        pass  # Return whatever we have so far

    return tokens
