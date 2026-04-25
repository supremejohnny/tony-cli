"""
Card renderer — one item per slide, with section headings.

Fill format:
    {
        "title": "Slide header shown on every slide",
        "items": [
            {
                "title": "Card title (large)",
                "body": "Optional plain body text",
                "sections": [
                    {"heading": "Section A", "body": "..."},
                    {"heading": "Section B", "body": "..."}
                ]
            }
        ]
    }

If 'sections' is present it overrides 'body'. Each item becomes one slide.
Paginates at max_items (default 6).
"""
from ._common import (
    accent, add_rect, add_text, add_text_multiline,
    blank_layout, body_size, primary, rgb, slide_dims, title_size,
)

MAX_ITEMS = 6
BAR_W = 0.28  # left accent bar width in inches
MARGIN_L = BAR_W + 0.35
MARGIN_T = 0.30
MARGIN_R = 0.35


def render(prs, fill, tokens):
    """Add one slide per item to prs. Silently caps at MAX_ITEMS."""
    slide_title = fill.get("title", "")
    items = fill.get("items", [])[:MAX_ITEMS]

    layout = blank_layout(prs)
    for item in items:
        slide = prs.slides.add_slide(layout)
        _render_card_slide(slide, prs, slide_title, item, tokens)


def _render_card_slide(slide, prs, slide_title, item, tokens):
    w, h = slide_dims(prs)
    content_w = w - MARGIN_L - MARGIN_R
    pri = primary(tokens)
    acc0 = accent(tokens, 0)

    # Left accent bar
    add_rect(slide, 0, 0, BAR_W, h, pri)

    # Slide title (small, top)
    add_text(
        slide, slide_title,
        left=MARGIN_L, top=MARGIN_T, width=content_w, height=0.45,
        font_size=11, color_hex="#6B7280",
    )

    # Separator line (thin rect)
    add_rect(slide, MARGIN_L, MARGIN_T + 0.5, content_w, 0.02, "#E5E7EB")

    # Item title (large, bold)
    item_title = item.get("title", "")
    t_size = min(title_size(tokens), 36)
    add_text(
        slide, item_title,
        left=MARGIN_L, top=MARGIN_T + 0.65, width=content_w, height=0.9,
        font_size=t_size, bold=True, color_hex=pri,
    )

    # Content area: sections or plain body
    sections = item.get("sections")
    body = item.get("body", "")
    b_size = body_size(tokens)

    if sections:
        _render_sections(slide, sections, tokens, MARGIN_L, MARGIN_T + 1.65, content_w, h)
    elif body:
        add_text_multiline(
            slide, body.split("\n"),
            left=MARGIN_L, top=MARGIN_T + 1.65, width=content_w,
            height=h - MARGIN_T - 1.65 - 0.3,
            font_size=b_size, color_hex="#374151",
        )


def _render_sections(slide, sections, tokens, left, top, width, slide_h):
    b_size = body_size(tokens)
    n = len(sections)

    if n == 2:
        # Side by side
        col_w = (width - 0.25) / 2
        for i, sec in enumerate(sections):
            x = left + i * (col_w + 0.25)
            _render_one_section(slide, sec, tokens, x, top, col_w, slide_h - top - 0.3, b_size)
    else:
        # Stacked
        avail_h = slide_h - top - 0.3
        sec_h = avail_h / max(n, 1)
        for i, sec in enumerate(sections):
            _render_one_section(slide, sec, tokens, left, top + i * sec_h, width, sec_h - 0.1, b_size)


def _render_one_section(slide, sec, tokens, left, top, width, height, b_size):
    acc = accent(tokens, 0)
    heading = sec.get("heading", "").upper()
    body = sec.get("body", "")

    # Heading with accent color pill background
    add_rect(slide, left, top, width, 0.28, acc)
    add_text(
        slide, heading,
        left=left + 0.1, top=top + 0.03, width=width - 0.1, height=0.25,
        font_size=10, bold=True, color_hex="#FFFFFF",
    )

    # Body text
    add_text_multiline(
        slide, body.split("\n"),
        left=left, top=top + 0.33, width=width, height=max(height - 0.33, 0.3),
        font_size=b_size, color_hex="#374151",
    )
