# -*- coding: utf-8 -*-
r"""Number line with intervals and marked points.

A number line is the one figure where *the labels are the content*: a reader
answers "is -1 included?" by looking at whether the endpoint dot is filled,
and "where does the interval end?" by reading the number under it.  Both facts
are therefore drawn from the parameter, never inferred later:

* an interval endpoint is a **filled dot when included, a hollow ring when
  excluded** -- the textbook convention, and the only difference between
  ``[-1, 2)`` and ``[-1, 2]`` on the page;
* an **open end** (``b`` is ``None``) becomes a ray with an arrowhead, so
  ``[-1, +inf)`` cannot be mistaken for a closed interval that merely runs off
  the frame.

Every integer on the axis is labelled.  That is what makes the figure a number
line rather than a bar chart, and it also means an integer endpoint needs no
second label of its own -- printing both would put two numbers on one tick.
"""
import math

from .. import env, layout
from . import _helpers as H


def _ends(style):
    """``(left_included, right_included)`` for one interval style."""
    s = str(style or "closed").strip().lower()
    if s in ("open", "o", "()"):
        return False, False
    if s in ("lopen", "lo", "(]"):
        return False, True
    if s in ("ropen", "ro", "[)"):
        return True, False
    if s in ("none", "unbounded"):
        return False, False
    return True, True


def _norm_interval(item):
    """Accept ``[a, b]``, ``[a, b, style]``, or ``{"a":.., "b":.., "style":..}``."""
    if isinstance(item, dict):
        a = item.get("a", item.get("lo"))
        b = item.get("b", item.get("hi"))
        style = item.get("style", "closed")
    elif isinstance(item, (list, tuple)):
        if len(item) < 2:
            raise ValueError("an interval needs two ends: %r" % (item,))
        a, b = item[0], item[1]
        style = item[2] if len(item) > 2 else "closed"
    else:
        raise ValueError("cannot read interval %r" % (item,))
    a = None if a is None else float(a)
    b = None if b is None else float(b)
    if a is not None and b is not None and b < a:
        a, b = b, a
        left_in, right_in = _ends(style)
        style = {(True, True): "closed", (False, False): "open",
                 (True, False): "ropen", (False, True): "lopen"}[
                     (right_in, left_in)]
    return a, b, style


def _tick_step(span, want=12):
    """A tick spacing that keeps at most ~``want`` labels on the axis."""
    step = 1
    for cand in (1, 2, 5, 10, 20, 50, 100):
        step = cand
        if span / step <= want:
            break
    return step


def numberline(lo=-4.0, hi=6.0, intervals=((-1.0, 2.0, "closed"),),
               points=(), out_path="math_numberline.png"):
    """A horizontal axis with shaded intervals and marked points.

    ``intervals`` is a list of ``[a, b, style]``.  ``a`` or ``b`` may be
    ``None`` for an unbounded end.  ``style`` is ``closed``, ``open``,
    ``lopen`` (left end open), ``ropen`` (right end open) or ``none``.
    ``points`` is a list of numbers to mark on the axis.
    """
    plt = env.pyplot()
    lo, hi = float(lo), float(hi)
    if hi <= lo:
        raise ValueError("hi must exceed lo")

    items = [_norm_interval(it) for it in (intervals or ())]
    pts = [float(p) for p in (points or [])]
    for a, b, _s in items:
        for v in (a, b):
            if v is not None and not (lo - 1e-9 <= v <= hi + 1e-9):
                raise ValueError(
                    "interval end %g is outside the axis [%g, %g]; widen lo/hi"
                    % (v, lo, hi))
    for p in pts:
        if not (lo - 1e-9 <= p <= hi + 1e-9):
            raise ValueError("point %g is outside the axis [%g, %g]; widen lo/hi"
                             % (p, lo, hi))

    n_levels = max(1, len(items))
    y_band0 = 0.66
    y_band_step = 0.50
    y_top = y_band0 + y_band_step * (n_levels - 1)
    y_lo, y_hi = -1.00, y_top + 0.52

    fig, ax = plt.subplots(figsize=(6.0, 1.45 + 0.40 * n_levels), dpi=300)

    painted = []

    # The axis itself: a horizontal arrow at y = 0.  A number line has no
    # y-axis and no origin label -- the axis *is* the number set.
    ax.annotate("", xy=(hi, 0), xytext=(lo, 0),
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.3,
                                mutation_scale=12, shrinkA=0, shrinkB=0),
                zorder=3)
    ax.text(hi, 0.13, "$x$", fontsize=10.5, ha="right", va="bottom")
    painted.append("$x$")

    step = _tick_step(hi - lo)
    first = int(math.ceil(lo / step)) * step
    tick_vals = list(range(first, int(math.floor(hi)) + 1, step))
    for v in tick_vals:
        ax.plot([v, v], [-0.10, 0.10], color="#1a1a1a", lw=1.0, zorder=3)
        ax.text(v, -0.20, H.fmt(v), fontsize=9.5, ha="center", va="top")
        painted.append(H.fmt(v))

    # Marked points sit just above the axis, clear of the tick labels below.
    for p in pts:
        H.dot(ax, p, 0.0, filled=True, ms=5.2)
        if abs(p - round(p)) > 1e-9 or p not in tick_vals:
            ax.text(p, 0.18, H.fmt(p), fontsize=9.5, ha="center", va="bottom")
            painted.append(H.fmt(p))

    # One band per interval, stacked so two of them can share an axis without
    # one hiding the other.
    for i, (a, b, style) in enumerate(items):
        y = y_band0 + y_band_step * i
        left_in, right_in = _ends(style)
        x_start = a if a is not None else lo
        x_stop = b if b is not None else hi
        ax.plot([x_start, x_stop], [y, y], color="#1565c0", lw=3.4,
                solid_capstyle="butt", zorder=4)
        for end, included, outward in ((a, left_in, -1), (b, right_in, +1)):
            if end is None:
                # An unbounded end is a ray: the arrowhead says "continues".
                x0 = lo if outward < 0 else hi
                H.arrow(ax, (x0, y), (x0 + outward * 0.32, y),
                        color="#1565c0", lw=1.8, zorder=5)
                continue
            H.dot(ax, end, y, filled=included, color="#1565c0", ms=6.2)
            if end not in tick_vals:
                ax.text(end, y + 0.16, H.fmt(end), fontsize=9.5,
                        color="#1565c0", ha="center", va="bottom")
                painted.append(H.fmt(end))

    ax.set_xlim(lo - 0.30, hi + 0.30)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    # `$x$` sits at the tip of the arrow it names.
    report = layout.finish(fig, ax, out_path, skip=("$x$",))
    return {
        "intervals": [[a, b, s] for a, b, s in items],
        "points": pts,
        "marks": set(painted),
        "layout": report,
    }
