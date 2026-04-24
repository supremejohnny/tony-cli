"""
Card grid renderer — 2x2 or 3x1 grid of cards.

Fill:
    {
        "title": "Grid title",
        "items": [
            {"heading": "Card 1", "body": "Description..."},
            ...
        ]
    }
Max 4 items. 1-2 items: single row. 3 items: 3x1. 4 items: 2x2.
"""
from ._common import (
    brand_accent, add_rect, add_text, add_text_multiline,
    blank_layout, body_size, text_color, title_size, slide_dims,
)

MAX_ITEMS = 4
MARGIN_L = 0.4
MARGIN_T = 0.25
MARGIN_R = 0.4
CARD_GAP = 0.18
TITLE_H = 0.65
ACCENT_BAR_H = 0.07


def render(prs, fill, tokens):
    items = fill.get("items", [])[:MAX_ITEMS]
    if not items:
        return

    layout = blank_layout(prs)
    slide = prs.slides.add_slide(layout)
    _render_grid(slide, prs, fill.get("title", ""), items, tokens)


def _render_grid(slide, prs, title, items, tokens):
    w, h = slide_dims(prs)
    n = len(items)
    txt = text_color(tokens)
    b_size = body_size(tokens)
    t_size = min(title_size(tokens), 28)

    content_w = w - MARGIN_L - MARGIN_R
    grid_top = MARGIN_T + TITLE_H
    grid_h = h - grid_top - 0.25

    add_text(
        slide, title,
        left=MARGIN_L, top=MARGIN_T, width=content_w, height=TITLE_H - 0.1,
        font_size=t_size, bold=True, color_hex=txt,
    )

    if n <= 3:
        cols, rows = n, 1
    else:
        cols, rows = 2, 2

    card_w = (content_w - CARD_GAP * (cols - 1)) / cols
    card_h = (grid_h - CARD_GAP * (rows - 1)) / rows

    for i, item in enumerate(items):
        row, col = divmod(i, cols)
        x = MARGIN_L + col * (card_w + CARD_GAP)
        y = grid_top + row * (card_h + CARD_GAP)
        acc = brand_accent(tokens, i)

        # Left accent border
        add_rect(slide, x, y, ACCENT_BAR_H, card_h, acc)

        # Heading
        add_text(
            slide, item.get("heading", ""),
            left=x + 0.15, top=y + 0.1, width=card_w - 0.2, height=0.42,
            font_size=b_size + 1, bold=True, color_hex=acc,
        )

        # Body
        body = item.get("body", "")
        if body:
            add_text_multiline(
                slide, body.split("\n"),
                left=x + 0.15, top=y + 0.55, width=card_w - 0.2, height=card_h - 0.65,
                font_size=max(b_size - 1, 9), color_hex=txt,
            )
