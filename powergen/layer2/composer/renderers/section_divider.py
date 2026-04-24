"""
Section divider renderer — large title + optional subtitle.

Fill: {"title": "Section Name", "subtitle": "Optional subtitle"}
"""
from pptx.enum.text import PP_ALIGN

from ._common import (
    brand_accent, add_rect, add_text, blank_layout,
    heading_font_name, slide_dims, text_color, title_size, body_size,
)

MARGIN_H = 0.6
ACCENT_BAR_H = 0.08


def render(prs, fill, tokens):
    layout = blank_layout(prs)
    slide = prs.slides.add_slide(layout)
    w, h = slide_dims(prs)

    title = fill.get("title", "")
    subtitle = fill.get("subtitle", "")
    acc = brand_accent(tokens)
    txt = text_color(tokens)
    t_size = min(title_size(tokens), 54)
    b_size = body_size(tokens) + 2
    content_w = w - MARGIN_H * 2

    # Top + bottom accent bars
    add_rect(slide, 0, 0, w, ACCENT_BAR_H, acc)
    add_rect(slide, 0, h - ACCENT_BAR_H, w, ACCENT_BAR_H, acc)

    # Title — vertically centered
    title_top = h * 0.33
    add_text(
        slide, title,
        left=MARGIN_H, top=title_top, width=content_w, height=1.4,
        font_size=t_size, bold=True, color_hex=txt,
        align=PP_ALIGN.LEFT, font_name=heading_font_name(tokens),
    )

    if subtitle:
        add_text(
            slide, subtitle,
            left=MARGIN_H, top=title_top + 1.5, width=content_w, height=0.6,
            font_size=b_size, color_hex=acc,
            align=PP_ALIGN.LEFT,
        )
