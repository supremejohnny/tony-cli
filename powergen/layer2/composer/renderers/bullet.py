"""
Bullet renderer — flat list of independent points on one slide.

Fill format:
    {
        "title": "Slide title",
        "items": ["Point one", "Point two", "Point three"]
    }

Falls back to two-column layout above 5 items. Max 8 items.
"""
from ._common import (
    accent, add_rect, add_text, add_text_multiline,
    blank_layout, body_size, primary, slide_dims, title_size,
)

MAX_ITEMS = 8
BAR_W = 0.28
MARGIN_L = BAR_W + 0.35
MARGIN_T = 0.30
MARGIN_R = 0.35
BULLET_CHAR = "•"


def render(prs, fill, tokens):
    """Add one bullet slide to prs."""
    slide_title = fill.get("title", "")
    items = fill.get("items", [])[:MAX_ITEMS]

    layout = blank_layout(prs)
    slide = prs.slides.add_slide(layout)
    _render_bullet_slide(slide, prs, slide_title, items, tokens)


def _render_bullet_slide(slide, prs, slide_title, items, tokens):
    w, h = slide_dims(prs)
    content_w = w - MARGIN_L - MARGIN_R
    pri = primary(tokens)
    b_size = body_size(tokens)
    t_size = min(title_size(tokens), 36)

    # Left accent bar
    add_rect(slide, 0, 0, BAR_W, h, pri)

    # Slide title
    add_text(
        slide, slide_title,
        left=MARGIN_L, top=MARGIN_T, width=content_w, height=0.8,
        font_size=t_size, bold=True, color_hex=pri,
    )

    content_top = MARGIN_T + 0.95
    avail_h = h - content_top - 0.3

    if len(items) <= 5:
        _render_single_column(slide, items, tokens, MARGIN_L, content_top, content_w, avail_h, b_size)
    else:
        _render_two_column(slide, items, tokens, MARGIN_L, content_top, content_w, avail_h, b_size)


def _render_single_column(slide, items, tokens, left, top, width, height, b_size):
    acc = accent(tokens, 0)
    item_h = height / max(len(items), 1)

    for i, text in enumerate(items):
        y = top + i * item_h
        # Bullet dot
        add_rect(slide, left, y + item_h * 0.35, 0.12, 0.12, acc)
        add_text(
            slide, text,
            left=left + 0.22, top=y, width=width - 0.22, height=item_h - 0.05,
            font_size=b_size, color_hex="#1F2937", word_wrap=True,
        )


def _render_two_column(slide, items, tokens, left, top, width, height, b_size):
    acc = accent(tokens, 0)
    mid = (len(items) + 1) // 2
    col_w = (width - 0.3) / 2
    col_x = [left, left + col_w + 0.3]

    for col_idx, col_items in enumerate([items[:mid], items[mid:]]):
        item_h = height / max(len(col_items), 1)
        x = col_x[col_idx]
        for j, text in enumerate(col_items):
            y = top + j * item_h
            add_rect(slide, x, y + item_h * 0.35, 0.12, 0.12, acc)
            add_text(
                slide, text,
                left=x + 0.22, top=y, width=col_w - 0.22, height=item_h - 0.05,
                font_size=b_size, color_hex="#1F2937", word_wrap=True,
            )
