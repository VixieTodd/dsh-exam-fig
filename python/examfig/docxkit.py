# -*- coding: utf-8 -*-
"""python-docx helpers shared by the paper builder.

Everything here exists because of a rendering bug seen in a real page:

* **Left-align Chinese paragraphs.**  Justified (the default for CJK text in
  Word) stretches short lines character by character; a four-word answer line
  came out as ``\u9876 \u70b9 \u7eb5 \u5750 \u6807`` with gaps between every glyph.
* **Bind figures to their captions.**  ``keep_with_next`` on the image
  paragraph stops Word from leaving the picture at the bottom of a page and the
  caption at the top of the next.
* **Size by aspect ratio, not by a fixed width.**  A fixed width makes a wide
  flat circuit diagram 2.7 cm tall and a tall triangle 6.9 cm tall; the first
  becomes unreadable and the second eats half a page.  Compute the width from
  a target *height* instead, then clamp.
"""
import struct

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

# Target height for a figure, with the width allowed to move inside a band.
FIG_TARGET_H_CM = 4.3
FIG_MAX_W_CM = 7.6
FIG_MIN_W_CM = 3.6

SONG = "SimSun"
HEI = "SimHei"
TNR = "Times New Roman"


def png_size(path):
    """``(width, height)`` from a PNG's IHDR, without loading the image."""
    with open(path, "rb") as f:
        head = f.read(33)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG: %s" % path)
    return struct.unpack(">II", head[16:24])


def figure_width(path):
    """A width that keeps the figure near ``FIG_TARGET_H_CM`` tall."""
    w_px, h_px = png_size(path)
    if h_px <= 0:
        return Cm(FIG_MIN_W_CM)
    width_cm = FIG_TARGET_H_CM * (w_px / float(h_px))
    width_cm = max(FIG_MIN_W_CM, min(FIG_MAX_W_CM, width_cm))
    return Cm(width_cm)


def set_run_font(run, name, size=None, bold=None, latin=None):
    """Set both the Latin and the East-Asian face of a run.

    python-docx only sets ``w:rFonts/@w:ascii`` through ``run.font.name``;
    Chinese characters then fall back to whatever the theme says, which is how
    a "SimSun" paragraph ends up half SimHei.
    """
    from docx.oxml.ns import qn
    run.font.name = latin or name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), name)
    rfonts.set(qn("w:ascii"), latin or name)
    rfonts.set(qn("w:hAnsi"), latin or name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold


def body_paragraph(doc, align_left=True):
    """A body paragraph in the house style: SimSun 10.5 pt, 1.5 line spacing."""
    p = doc.add_paragraph()
    if align_left:
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(0)
    return p


def title(doc, text, size=15):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_run_font(run, HEI, size, bold=True)
    p.paragraph_format.space_after = Pt(10)
    return p


def section(doc, text, size=13):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_run_font(run, HEI, size, bold=True)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(8)
    return p


def answer_paragraph(doc):
    """An answer line: left aligned, no indent, tight spacing."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.4
    return p


def figure_paragraph(doc, path, caption=None, caption_size=9):
    """Insert a PNG, sized by aspect ratio, with its caption bound to it."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(path, width=figure_width(path))

    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_before = Pt(0)
        cap.paragraph_format.space_after = Pt(6)
        run = cap.add_run(caption)
        set_run_font(run, SONG, caption_size)
    return p


def rich(doc, parts, paragraph=None, align_left=True):
    """Build a paragraph from mixed parts.

    ``parts`` is a list of

    ``('t', text)``            plain text
    ``('m', latex)``           native Word equation
    ``('c', [(txt, sub)])``    chemical formula with real subscripts
    """
    p = paragraph or body_paragraph(doc, align_left=align_left)
    for part in parts:
        kind = part[0]
        if kind == "t":
            run = p.add_run(part[1])
            set_run_font(run, SONG, 10.5, latin=TNR)
        elif kind == "m":
            from .omml import add_tex
            add_tex(p, part[1])
        elif kind == "c":
            for txt, is_sub in part[1]:
                run = p.add_run(txt)
                set_run_font(run, SONG, 10.5, latin=TNR)
                if is_sub:
                    run.font.subscript = True
        else:
            raise ValueError("unknown part kind: %r" % (kind,))
    return p


def normalize(doc):
    """Apply the document-wide defaults."""
    style = doc.styles["Normal"]
    style.font.name = TNR
    style.font.size = Pt(10.5)
    from docx.oxml.ns import qn
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), SONG)
    style.paragraph_format.line_spacing = 1.5
    return style
