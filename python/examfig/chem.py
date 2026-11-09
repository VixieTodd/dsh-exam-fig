# -*- coding: utf-8 -*-
"""Chemical formulae and equations as ordinary text runs.

Why not OMML?  Two independent reasons, both verified on a real document:

* ``\\mathrm{H}_{2}`` (subscript *outside* ``\\mathrm``) makes latex2mathml
  emit ``<mi>&#x00048;</mi>`` -- a numeric character reference that loses the
  ``mathvariant`` attribute -- so Word typesets ``H2`` as two italic
  variables.  Wrapping the whole thing (``\\mathrm{H_{2}}``) fixes the XML,
  but then:
* LibreOffice (and several other consumers) ignore ``m:sty m:val="p"`` when
  importing OMML and italicise it anyway.

A plain run with ``font.subscript = True`` is understood by every renderer
that has ever existed, so formulae are emitted as text.  Equations follow the
Chinese textbook convention the user asked for: ``=`` for inorganic chemistry,
``->`` for organic chemistry, with the reaction condition written between the
two halves of the symbol.

The subtle part is deciding which digits are subscripts.  In ``2H2 + O2`` the
leading ``2`` is a coefficient (full size) while the trailing ones are
subscripts; in ``Ca(OH)2`` the ``2`` after the parenthesis is a subscript; in
``Al2(SO4)3`` every digit except a leading coefficient is.
"""
import re

_TOKEN_RE = re.compile(r"[A-Z][a-z]?|\d+|[^\w]")

INORGANIC = "="
ORGANIC = "\u2192"          # ->


def parse_formula(formula):
    """Split a formula into ``[(text, is_subscript), ...]``.

    ``'2H2O'`` -> ``[('2', False), ('H', False), ('2', True), ('O', False)]``
    """
    s = formula.strip()
    out = []
    tokens = _TOKEN_RE.findall(s)
    for i, tok in enumerate(tokens):
        if not tok.isdigit():
            out.append((tok, False))
            continue
        prev = tokens[i - 1] if i else ""
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        # A digit is a subscript when it follows an element symbol or a closing
        # parenthesis, and is not itself followed by another digit (which would
        # make it part of a multi-digit count -- still a subscript, so the
        # "not nxt.isdigit()" guard only avoids splitting runs).
        is_sub = (prev[:1].isupper() or prev == ")") and not nxt.isdigit()
        out.append((tok, is_sub))
    # Coalesce adjacent tokens of the same kind so the document gets one run
    # per contiguous piece instead of one run per character.
    merged = []
    for txt, sub in out:
        if merged and merged[-1][1] == sub:
            merged[-1] = (merged[-1][0] + txt, sub)
        else:
            merged.append((txt, sub))
    return merged


def formula_runs(formula):
    """Alias kept for readability at call sites that build whole equations."""
    return parse_formula(formula)


def equation_parts(lhs, rhs, condition="", organic=True):
    """Build the ``parts`` list understood by :func:`examfig.docxkit.rich`.

    ``equation_parts('C2H5OH + 3O2', '2CO2 + 3H2O', '点燃')`` gives

        [('c', [('C',False), ('2',True), ...]), ('t', ' \u2192点燃\u2192 '), ...]

    The symbol is written on both sides of the condition, which is exactly how
    the PEP textbook prints it.
    """
    sym = ORGANIC if organic else INORGANIC
    mid = "%s%s%s" % (sym, condition, sym) if condition else sym
    parts = [("c", parse_formula(lhs)), ("t", " " + mid + " ")]
    parts += [("c", parse_formula(rhs))]
    return parts


def equation(lhs, rhs, condition="", organic=True):
    """One-line plain-text rendering, for logs and assertions."""
    sym = ORGANIC if organic else INORGANIC
    mid = "%s%s%s" % (sym, condition, sym) if condition else sym
    return "%s %s %s" % (lhs, mid, rhs)


def formula_latex(formula):
    """LaTeX with the whole formula inside ``\\mathrm``.

    Kept for callers that want the equation in a maths context (e.g. inside a
    larger derivation).  Prefer :func:`parse_formula` for standalone formulae.
    """
    pieces = []
    for tok in _TOKEN_RE.findall(formula.strip()):
        if tok.isdigit():
            pieces.append("_{%s}" % tok)
        else:
            pieces.append(tok)
    body = "".join(pieces)
    # The first token is a coefficient if the formula starts with a digit.
    if body.startswith("_{"):
        body = body[2:-1] + body[body.index("}") + 1:]
    return r"\mathrm{%s}" % body


def latex_equation(lhs, rhs, condition="", organic=True):
    """Full equation in LaTeX, for :func:`examfig.omml.add_tex`.

    Uses ``\\stackrel`` -- ``\\xrightarrow`` produces an empty box because it
    lowers to ``m:limUpp`` + ``m:phant``.
    """
    sym = r"\rightarrow" if organic else "="
    mid = r"\stackrel{%s}{%s}" % (condition, sym) if condition else sym
    return "%s %s %s" % (formula_latex(lhs), mid, formula_latex(rhs))
