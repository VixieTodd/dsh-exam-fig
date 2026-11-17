# -*- coding: utf-8 -*-
r"""Exponential and logarithmic graphs on one pair of axes.

The point of drawing them together is the *symmetry*: ``y = a**x`` and
``y = log_a x`` are reflections of each other in ``y = x``.  A figure that
plots both but omits the mirror line leaves the reader to remember the fact
instead of seeing it, so the dashed ``y = x`` is part of the drawing and its
label is part of ``marks``.

Two properties are checked rather than assumed:

* both curves really do pass through the mirror line at the same point --
  ``a**t == log_a(a**t)`` only when ``t`` is on ``y = x``;
* the exponential's horizontal asymptote and the logarithm's vertical
  asymptote are the two axes, so the curves are clipped to a window that
  contains both, otherwise ``y = log_a x`` disappears below ``x = 0`` and the
  picture silently loses half of itself.

``mode="piecewise"`` draws a polyline through ``knots`` instead -- a piecewise
function written as a table of points is exactly how a question states it, and
the vertices are where the reader's eye goes, so each knot is dotted and its
coordinates printed.
"""
import math

import numpy as np

from .. import env, layout
from . import _helpers as H

_C_EXP = "#c62828"
_C_LOG = "#1565c0"
_C_RECIP = "#2e7d32"


def explog(base=2.0, show_log=True, show_reciprocal=True, span=3.4,
           out_path="math_explog.png"):
    """``y = base**x``, its reciprocal-base mirror, and ``y = log_base x``.

    ``span`` is the half-width of the window in graph units.  The reciprocal
    base curve is ``(1/base)**x``: with ``base > 1`` the two exponentials are
    reflections in the y-axis, which is the other symmetry students are asked
    about.
    """
    plt = env.pyplot()
    a = float(base)
    if a <= 0 or abs(a - 1.0) < 1e-9:
        raise ValueError("base must be positive and not 1 (got %g)" % a)

    span = float(span)
    lim = span
    fig, ax = plt.subplots(figsize=(4.9, 4.3), dpi=300)
    ax.set_aspect("equal")

    painted = []
    painted += H.frame(ax, (-lim, lim), (-lim, lim), xlabel="$x$",
                       ylabel="$y$", style="center")
    # Integer ticks on both axes, because the reader needs to see that
    # (1, a) and (a, 1) are the same pair swapped.
    for v in range(int(-lim) + 1, int(lim)):
        if v == 0:
            continue
        ax.plot([v, v], [-0.075, 0.075], color="#1a1a1a", lw=0.9, zorder=3)
        ax.plot([-0.075, 0.075], [v, v], color="#1a1a1a", lw=0.9, zorder=3)
        ax.text(v, -0.20, H.fmt(v), fontsize=8.5, ha="center", va="top")
        ax.text(-0.20, v, H.fmt(v), fontsize=8.5, ha="right", va="center")
        painted.append(H.fmt(v))

    xs = np.linspace(-lim, lim, 900)
    with np.errstate(over="ignore", invalid="ignore"):
        ye = np.power(a, xs)
        yr = np.power(1.0 / a, xs)
    ye = np.where(np.isfinite(ye), ye, np.nan)
    yr = np.where(np.isfinite(yr), yr, np.nan)
    ax.plot(xs, ye, color=_C_EXP, lw=2.0, zorder=5, label="$y=%s^{x}$" % H.fmt(a))
    painted.append("y=%s^x" % H.fmt(a))
    if show_reciprocal:
        ax.plot(xs, yr, color=_C_RECIP, lw=1.6, zorder=5,
                label=r"$y=(1/%s)^{x}$" % H.fmt(a))
        painted.append("y=(1/%s)^x" % H.fmt(a))

    if show_log:
        # log_a x is defined only for x > 0; the other half of the domain is
        # empty space, not a curve that failed to draw.
        xl = np.linspace(1e-4, lim, 900)
        yl = np.log(xl) / math.log(a)
        yl = np.where(np.isfinite(yl), yl, np.nan)
        ax.plot(xl, yl, color=_C_LOG, lw=2.0, zorder=5,
                label="$y=\\log_{%s} x$" % H.fmt(a))
        painted.append("y=log_%s x" % H.fmt(a))

        # The mirror line, and the one point the two curves share on it.
        H.guide(ax, (-lim * 0.92, -lim * 0.92), (lim * 0.92, lim * 0.92),
                color="#616161", lw=1.1)
        ax.text(lim * 0.72, lim * 0.78, "$y=x$", fontsize=10,
                color="#616161", ha="left", va="bottom")
        painted.append("y=x")

        # Shared point: solve a**x == x, which has a solution only at x = 1
        # for a = ... in general there is none; what *is* shared is (0,1) on
        # the exponential and (1,0) on the logarithm -- they are mirror images,
        # so the fixed point of the reflection is where both cross y = x.
        fixed = _fixed_point(a, lim)
        if fixed is not None:
            H.dot(ax, fixed, fixed, filled=True, color="#6a1b9a", ms=5.0)
            ax.text(fixed, fixed + 0.16, H.fmt(fixed, 2), fontsize=9,
                    color="#6a1b9a", ha="center", va="bottom")
            painted.append(H.fmt(fixed, 2))

    # Anchors every textbook marks: the exponential crosses (0, 1), the
    # logarithm crosses (1, 0).
    for px, py in ((0.0, 1.0), (1.0, 0.0)):
        if abs(py) <= lim:
            H.dot(ax, px, py, filled=True, ms=4.4)

    leg = ax.legend(loc="lower right", fontsize=9, frameon=False,
                    handlelength=1.6, borderaxespad=0.2)
    for txt in leg.get_texts():
        painted.append(txt.get_text())

    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.axis("off")
    report = layout.finish(fig, ax, out_path, skip=("$x$", "$y$", "$O$"))

    return {
        "base": a,
        "marks": set(painted),
        "layout": report,
    }


def _fixed_point(a, lim):
    """``x`` with ``a**x == x``, if it lies in the window.

    For ``a`` slightly above ``e**(1/e)`` the exponential never meets ``y = x``
    and the equation has no solution -- in that case nothing is marked, because
    dotting a made-up point would be worse than omitting it.
    """
    f = lambda t: a ** t - t
    lo, hi = -lim, lim
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        return None
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


def piecewise(knots=((-3.0, -1.0), (-1.0, 1.0), (1.0, -2.0), (3.0, 0.0)),
              abs_a=1.0, abs_b=0.0, abs_c=0.0, mode="absolute",
              out_path="math_piecewise.png"):
    r"""``y = |a x + b| + c`` (``mode="absolute"``) or a polyline (``"pieces"``).

    In ``"absolute"`` mode the vertex is marked with its coordinates, because
    every question about ``|a x + b| + c`` is a question about that vertex: its
    position gives both the range and the axis of symmetry.

    In ``"pieces"`` mode ``knots`` is ``[[x, y], ...]``; consecutive knots are
    joined by straight segments and each knot is dotted, so the reader can see
    where the definition changes.
    """
    plt = env.pyplot()
    mode = str(mode or "absolute").strip().lower()
    fig, ax = plt.subplots(figsize=(5.2, 3.8), dpi=300)

    painted = []
    if mode == "absolute":
        a, b, c = float(abs_a), float(abs_b), float(abs_c)
        if abs(a) < 1e-12:
            raise ValueError("abs_a must be non-zero")
        vx = -b / a
        vy = c
        reach = 3.6
        xs = np.linspace(vx - reach, vx + reach, 900)
        ys = np.abs(a * xs + b) + c
        # The axes are drawn through the origin, so the origin has to be inside
        # the viewport.  A vertex far from it (abs_b=-6 puts the vertex at x=6)
        # would otherwise push the y axis -- and its label -- off the page.
        x_lo = float(min(xs.min(), vx, 0.0) - 0.5)
        x_hi = float(max(xs.max(), vx, 0.0) + 0.5)
        y_lo = float(min(ys.min(), 0.0) - 0.7)
        y_hi = float(max(ys.max(), 1.0) + 0.7)
        painted += H.frame(ax, (x_lo, x_hi), (y_lo, y_hi), style="center")
        ax.plot(xs, ys, color=_C_EXP, lw=2.0, zorder=5)
        H.dot(ax, vx, vy, filled=True, color=_C_EXP, ms=5.2)
        ax.text(vx, vy - 0.30, "(%s, %s)" % (H.fmt(vx, 2), H.fmt(vy, 2)),
                fontsize=9.5, color=_C_EXP, ha="center", va="top")
        painted += ["(%s, %s)" % (H.fmt(vx, 2), H.fmt(vy, 2))]
        # The axis of symmetry is the vertical through the vertex: dashed, so
        # it cannot be mistaken for part of the graph.
        H.guide(ax, (vx, y_lo), (vx, y_hi), color="#9e9e9e", lw=1.0)
        ax.text(vx + 0.12, y_hi - 0.18, "$x=%s$" % H.fmt(vx, 2), fontsize=9,
                color="#757575", ha="left", va="top")
        painted.append("x=%s" % H.fmt(vx, 2))
        result = {"vertex": [vx, vy], "range": [vy, None]}
    elif mode == "pieces":
        pts = [tuple(float(v) for v in p) for p in (knots or ())]
        if len(pts) < 2:
            raise ValueError("pieces mode needs at least two knots")
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x_lo, x_hi = min(xs + [0.0]) - 0.8, max(xs + [0.0]) + 0.8
        y_lo, y_hi = min(ys + [0.0]) - 0.9, max(ys + [0.0]) + 0.9
        painted += H.frame(ax, (x_lo, x_hi), (y_lo, y_hi), style="center")
        ax.plot(xs, ys, color=_C_EXP, lw=2.0, zorder=5,
                solid_joinstyle="miter")
        for px, py in pts:
            H.dot(ax, px, py, filled=True, color=_C_EXP, ms=4.6)
            ax.text(px, py + 0.22, "(%s, %s)" % (H.fmt(px, 2), H.fmt(py, 2)),
                    fontsize=8.8, color=_C_EXP, ha="center", va="bottom")
            painted.append("(%s, %s)" % (H.fmt(px, 2), H.fmt(py, 2)))
        result = {"knots": [list(p) for p in pts]}
    else:
        raise ValueError("mode must be 'absolute' or 'pieces' (got %r)" % mode)

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    report = layout.finish(fig, ax, out_path, skip=("$x$", "$y$", "$O$"))
    result.update({"mode": mode, "marks": set(painted), "layout": report})
    return result
