# -*- coding: utf-8 -*-
"""Fourth-level verification: does the figure agree with the question?

A figure can be beautifully drawn and still be wrong -- the right angle put on
the wrong vertex, a component arrow drawn at full length instead of
``G\\sin\\theta``, ``R_2`` labelled where ``R_1`` should be.  Those errors are
invisible to pixel diffing and to any check that looks only at the image.

This module compares two *declared* sets instead:

* ``need`` -- what the question stem says the figure must show, written by
  whoever wrote the question;
* ``marks`` -- what the drawing function returns as "these are the labels I
  actually painted".

Both sides are normalised through :func:`canon` and compared by containment.
Because the right-hand side comes from the drawing code rather than from the
image, an error of the kind above (a mislabelled vertex) shows up as a missing
mark, which is exactly the failure we want.

An earlier version derived ``need`` by regex over the question's LaTeX.  It
produced three false failures out of six questions -- ``R`` plucked out of
``\\mathrm{Rt}``, ``G_{\\parallel}`` and ``G\\parallel`` counted as two
different symbols, ``R_1`` never matching ``R_1=2``.  **A false alarm is worse
than no check**, because it teaches the reader to ignore the output.
"""
import re

# Labels that carry no meaning for the comparison: axis names and the origin,
# which appear on many figures without being asserted by any question.
BENIGN = frozenset({"o", "x", "y", "\u03c9"})

_REF_RE = re.compile(r"\u56fe\s*(\d+)")


def canon(text):
    """Fold every spelling of the same symbol onto one key.

    ``G_{\\parallel}``, ``G\\parallel``, ``G_parallel`` and ``G\u2225`` all
    become ``gpar``.
    """
    if text is None:
        return ""
    t = str(text)
    t = t.replace("\\parallel", "par").replace("\\perp", "perp")
    t = t.replace("\\circ", "").replace("\u00b0", "")
    t = t.replace("\\mathrm", "").replace("\\text", "")
    t = t.replace("\u2225", "par").replace("\u22a5", "perp")
    # Substring, not \b: in "gparallel" the letters run together, so a word
    # boundary never matches and the symbol would stay unnormalised.
    t = t.replace("parallel", "par")
    for ch in "\\{}$":
        t = t.replace(ch, "")
    t = t.replace("_", "").replace("^", "")
    t = re.sub(r"\s+", "", t)
    return t.lower()


def canon_set(items):
    out = set()
    for it in items:
        c = canon(it)
        if c and c not in BENIGN:
            out.add(c)
    return out


def _matches(need, marks):
    """Containment, with guards that keep it from matching the wrong thing.

    The figure writes ``R_1=2\u03a9`` while the question only promises
    ``R_1``; the figure may also write ``6 V`` where the question says ``6``.
    Substring containment in either direction handles both.

    Two guards exist because plain containment produced real false passes:

    * A *letter* requirement must match exactly.  ``g`` is a substring of
      ``gperp``, so a question needing the weight ``G`` was silently satisfied
      by a figure that only painted ``G_\u22a5`` -- two different quantities.
    * A single *digit* may prefix-match, because the extra text is a unit:
      ``6`` against ``6v`` is the same number, and treating it as a miss sends
      the caller hunting for a label that is plainly on the page.
    """
    for m in marks:
        if need == m:
            return True
        if len(need) >= 2 and need in m:
            return True
        if len(m) >= 2 and m in need:
            return True
        if len(need) == 1 and need.isdigit() and m.startswith(need):
            return True
    return False


def check(specs, figures, strict_refs=True):
    """Compare declared requirements against painted marks.

    Parameters
    ----------
    specs
        ``[{'no': 1, 'need': [...], 'text': '...'}, ...]``
    figures
        ``{1: {'marks': [...]}, ...}`` -- the return value of each drawing
        function.

    Returns ``(ok, lines)`` where ``lines`` is a human-readable report.
    """
    lines = []
    ok = True

    for spec in specs:
        no = spec.get("no")
        need = list(spec.get("need") or [])
        fig = figures.get(no) if figures else None
        if fig is None:
            lines.append("FAIL [\u56fe %s] \u9898\u5e72\u5f15\u7528\u4e86\u56fe\uff0c\u4f46\u6ca1\u6709\u751f\u6210" % no)
            ok = False
            continue

        marks = canon_set(fig.get("marks") or [])
        missing = []
        for item in need:
            c = canon(item)
            if not c or c in BENIGN:
                continue
            if not _matches(c, marks):
                missing.append(item)
        if missing:
            ok = False
            lines.append("FAIL [\u56fe %s] \u9898\u5e72\u58f0\u660e\u7684\u6807\u6ce8\u672a\u753b\u51fa\uff1a%s\uff08\u56fe\u4e0a\u5b9e\u6709\uff1a%s\uff09"
                         % (no, "\u3001".join(missing), "\u3001".join(sorted(marks))))
        else:
            lines.append("PASS [\u56fe %s] %d \u9879\u6807\u6ce8\u4e00\u81f4" % (no, len(need)))

        extra = []
        for m in sorted(marks):
            if not any(_matches(canon(n), {m}) for n in need if canon(n)):
                extra.append(m)
        if extra:
            lines.append("WARN [\u56fe %s] \u56fe\u4e0a\u591a\u4f59\u6807\u6ce8\uff1a%s" % (no, "\u3001".join(extra)))

    if strict_refs:
        have = set(figures or ())
        for spec in specs:
            for no_in_text in _REF_RE.findall(str(spec.get("text") or "")):
                if int(no_in_text) not in have:
                    ok = False
                    lines.append("FAIL [\u9898 %s] \u6b63\u6587\u5f15\u7528\u4e86\u300c\u56fe %s\u300d\uff0c\u4f46\u8be5\u56fe\u4e0d\u5b58\u5728"
                                 % (spec.get("no"), no_in_text))
    return ok, lines
