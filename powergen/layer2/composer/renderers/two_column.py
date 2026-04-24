"""
Two-column renderer — two parallel sections side by side.

Fill:
    {
        "title": "Slide title",
        "items": [
            {"heading": "Left heading", "body": "Left body text"},
            {"heading": "Right heading", "body": "Right body text"}
        ]
    }
"""
from ._common import (
    brand_accent, add_rect, add_text, add_text_multiline,
    blank_layout, body_size, text_color, title_size, slide_dims,
)

MARGIN_L = 0.5
MARGIN_T = 0.25
MARGIN_R = 0.5
COL_GAP = 0.25
HEADER_H = 0.55


def render(prs, fill, tokens):
    items = fill.get("items", [])[:2]
    while len(items) < 2:
        items.append({"heading": "", "body": ""})

    layout = blank_layout(prs)
    slide = prs.slides.add_slide(layout)
    w, h = slide_dims(prs)

    title = fill.get("title", "")
    txt = text_color(tokens)
    t_size = min(title_size(tokens), 32)
    b_size = body_size(tokens)
    acc0, acc1 = brand_accent(tokens), brand_accent(tokens, 1)

    content_w = w - MARGIN_L - MARGIN_R
    col_w = (content_w - COL_GAP) / 2

    # Slide title
    add_text(
        slide, title,
        left=MARGIN_L, top=MARGIN_T, width=content_w, height=0.65,
        font_size=t_size, bold=True, color_hex=txt,
    )

    col_top = MARGIN_T + 0.8
    col_h = h - col_top - 0.3
    cols = [
        (MARGIN_L, acc0, items[0]),
        (MARGIN_L + col_w + COL_GAP, acc1, items[1]),
    ]

    for x, acc, item in cols:
        heading = item.get("heading", "")
        body = item.get("body", "")

        # Accent header bar
        add_rect(slide, x, col_top, col_w, HEADER_H, acc)

        # Heading text on bar
        add_text(
            slide, heading,
            left=x + 0.12, top=col_top + 0.08, width=col_w - 0.24, height=HEADER_H - 0.1,
            font_size=b_size + 1, bold=True, color_hex="#FFFFFF",
        )

        # Body text below bar
        body_top = col_top + HEADER_H + 0.12
        add_text_multiline(
            slide, body.split("\n"),
            left=x, top=body_top, width=col_w, height=col_h - HEADER_H - 0.12,
            font_size=b_size, color_hex=txt,
        )
