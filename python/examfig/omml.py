# -*- coding: utf-8 -*-
"""LaTeX -> native Word equations (OMML).

Word's own equation objects (*not* pictures, *not* MathType) are produced by
running MathML through Microsoft's ``MML2OMML.XSL`` stylesheet, which ships
with every copy of Office.  The recipe is:

    LaTeX --latex2mathml--> MathML --MML2OMML.XSL--> <m:oMath> --append--> w:p

Two details make the difference between "works" and "renders as tofu":

* **CJK inside a formula needs an explicit font.**  ``\\text{点燃}`` becomes a
  math run set in Cambria Math, which has no CJK glyphs.  :func:`_patch_cjk`
  rewrites the ``w:rFonts`` of exactly those runs.
* **Only ``\\stackrel`` survives.**  ``\\xrightarrow{...}`` lowers to
  ``m:limUpp`` + ``m:phant`` and ``\\longrightarrow`` has no glyph in Cambria
  Math; both render as an empty box.  Use ``\\stackrel{cond}{=}`` (inorganic)
  or ``\\stackrel{cond}{\\rightarrow}`` (organic).  :mod:`examfig.chem` goes
  further and avoids OMML for formulae entirely.
"""
import os
import re

from lxml import etree

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_M = "{%s}" % M_NS
_W = "{%s}" % W_NS

_CJK_RE = re.compile(r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]")

# Typical places the stylesheet hides.  Checked in order; the first hit wins.
_XSL_GUESSES = (
    r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL",
    r"C:\Program Files (x86)\Microsoft Office\root\Office16\MML2OMML.XSL",
    r"C:\Program Files\Microsoft Office\Office16\MML2OMML.XSL",
    r"C:\Program Files\Microsoft Office\Office15\MML2OMML.XSL",
    r"C:\Program Files (x86)\Microsoft Office\Office15\MML2OMML.XSL",
    r"C:\Program Files\Microsoft Office\Office14\MML2OMML.XSL",
    "/Applications/Microsoft Office 2011/Office/MML2OMML.XSL",
)

_state = {"xsl": None, "path": None, "tried": False}


class OmmlUnavailable(RuntimeError):
    """Raised when MML2OMML.XSL cannot be located."""


def find_stylesheet():
    """Locate ``MML2OMML.XSL``.

    Honours ``$DSH_EXAMFIG_MML2OMML`` first so that an unusual install can be
    pointed at explicitly, then probes the usual Office directories.
    """
    if _state["tried"]:
        return _state["path"]
    _state["tried"] = True

    env = os.environ.get("DSH_EXAMFIG_MML2OMML")
    if env and os.path.isfile(env):
        _state["path"] = env
        return env

    for guess in _XSL_GUESSES:
        if os.path.isfile(guess):
            _state["path"] = guess
            return guess

    # Last resort: a shallow sweep of the Office root, which catches
    # Click-to-Run installs whose OfficeNN folder was renamed.
    for root in (r"C:\Program Files\Microsoft Office",
                 r"C:\Program Files (x86)\Microsoft Office"):
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            if "MML2OMML.XSL" in filenames:
                found = os.path.join(dirpath, "MML2OMML.XSL")
                _state["path"] = found
                return found
            if dirpath.count(os.sep) - root.count(os.sep) > 3:
                _dirnames[:] = []
    return None


def _transform():
    if _state["xsl"] is not None:
        return _state["xsl"]
    path = find_stylesheet()
    if not path:
        raise OmmlUnavailable(
            "MML2OMML.XSL not found. It ships with Microsoft Office; set "
            "DSH_EXAMFIG_MML2OMML to its full path if Office lives elsewhere."
        )
    _state["xsl"] = etree.XSLT(etree.parse(path))
    return _state["xsl"]


def available():
    """True when equations can be produced on this machine."""
    try:
        _transform()
    except Exception:                    # noqa: BLE001 - any failure means "no"
        return False
    return True


def _patch_cjk(omath, font="SimSun"):
    """Give CJK runs a font that has the glyphs.

    Office leaves them in Cambria Math, so ``\\text{点燃}`` renders as two
    empty boxes even though the XML is correct.
    """
    for run in omath.iter(_M + "r"):
        texts = run.findall(_M + "t")
        if not any(_CJK_RE.search(t.text or "") for t in texts):
            continue
        rpr = run.find(_M + "rPr")
        if rpr is None:
            rpr = etree.SubElement(run, _M + "rPr")
            run.remove(rpr)
            run.insert(0, rpr)
        rfonts = rpr.find(_W + "rFonts")
        if rfonts is None:
            rfonts = etree.SubElement(rpr, _W + "rFonts")
        for attr in ("ascii", "eastAsia", "hAnsi"):
            rfonts.set(_W + attr, font)


def tex2omml(tex, cjk_font="SimSun"):
    """Return an ``<m:oMath>`` lxml element for a LaTeX fragment."""
    import latex2mathml.converter as l2m
    mathml = l2m.convert(tex)
    tree = etree.fromstring(mathml.encode("utf-8"))
    result = _transform()(tree)
    root = result.getroot()
    node = None
    for el in root.iter():
        tag = getattr(el, "tag", "")
        if isinstance(tag, str) and tag.endswith("}oMath"):
            node = el
            break
    if node is None:
        raise RuntimeError("MML2OMML produced no oMath for: %s" % tex)
    _patch_cjk(node, cjk_font)
    return node


def add_tex(paragraph, tex, cjk_font="SimSun"):
    """Append ``tex`` to a python-docx paragraph as a native equation."""
    paragraph._p.append(tex2omml(tex, cjk_font))
    return paragraph
