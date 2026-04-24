"""Shared utilities for all content-type renderers."""
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


def rgb(hex_str):
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def blank_layout(prs):
    for layout in prs.slide_layouts:
        if "blank" in layout.name.lower():
            return layout
    return min(prs.slide_layouts, key=lambda l: len(list(l.placeholders)))


def slide_dims(prs):
    from pptx.util import Emu
    return Emu(prs.slide_width).inches, Emu(prs.slide_height).inches


def add_rect(slide, left, top, width, height, fill_hex, line_hex=None):
    shape = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(left), Inches(top), Inches(width), Inches(height),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill_hex)
    border_color = fill_hex if line_hex is None else line_hex
    shape.line.color.rgb = rgb(border_color)
    return shape


def add_text(
    slide, text, left, top, width, height,
    font_size=12, bold=False, color_hex=None,
    align=PP_ALIGN.LEFT, word_wrap=True, italic=False, font_name=None,
):
    box = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = box.text_frame
    tf.word_wrap = word_wrap
    para = tf.paragraphs[0]
    para.alignment = align
    run = para.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    if color_hex:
        run.font.color.rgb = rgb(color_hex)
    if font_name:
        run.font.name = font_name
    return box


def add_text_multiline(
    slide, lines, left, top, width, height,
    font_size=12, bold=False, color_hex=None,
    align=PP_ALIGN.LEFT, word_wrap=True, font_name=None,
):
    box = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = box.text_frame
    tf.word_wrap = word_wrap
    for i, line in enumerate(lines):
        if i == 0:
            para = tf.paragraphs[0]
        else:
            para = tf.add_paragraph()
        para.alignment = align
        run = para.add_run()
        run.text = line
        run.font.size = Pt(font_size)
        run.font.bold = bold
        if color_hex:
            run.font.color.rgb = rgb(color_hex)
        if font_name:
            run.font.name = font_name
    return box


# --- Token accessors (support both v3 flat format and v1 nested format) ---

def primary(tokens):
    """Primary/dark color — used for titles and accent bars."""
    return tokens.get("dk1_hex") or tokens.get("primary_color", "#1F2937")


def accent(tokens, index=0):
    accents = tokens.get("accent_colors", ["#7578EC", "#F7B802", "#F18703", "#F35B06"])
    return accents[index % len(accents)] if accents else "#7578EC"


def brand_accent(tokens, offset=0):
    """Brand color of the template, identified by frequency analysis in schema_gen."""
    idx = tokens.get("brand_accent_index", 0) + offset
    return accent(tokens, idx)


def title_size(tokens):
    if "heading_size_pt" in tokens:
        return tokens["heading_size_pt"]
    return tokens.get("title_font", {}).get("size_pt_range", [28, 40])[1]


def body_size(tokens):
    if "body_size_pt" in tokens:
        return tokens["body_size_pt"]
    return tokens.get("body_font", {}).get("size_pt_range", [12, 16])[1]


def text_color(tokens):
    """Appropriate text color based on background darkness."""
    if tokens.get("bg_is_dark"):
        return tokens.get("lt1_hex", "#F5F5F5")
    return tokens.get("dk1_hex", "#1F2937")


def heading_font_name(tokens):
    return tokens.get("heading_font") or tokens.get("title_font", {}).get("name")


def body_font_name(tokens):
    return tokens.get("body_font") or tokens.get("body_font_obj", {}).get("name")
