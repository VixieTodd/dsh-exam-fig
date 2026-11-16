# -*- coding: utf-8 -*-
"""Shared drawing primitives for the figure modules.

Several figures in this package draw the same things: a coordinate frame with
arrowheads, a number printed the way a textbook prints it, a dot with its
value, a dimension bracket.  They live here for one reason -- a defect in any
of them would otherwise appear in every figure that re-implements it, and
there would be no single place to fix it.

The convention that matters: **every label painted here is returned to the
caller**, so a drawing function can add it to its ``marks`` without ever
re-reading the rendered image.
"""
import math

# Axis names and the origin.  Every figure with a coordinate frame paints
# these three, and each is *meant* to touch the stroke it names, so the
# collision audit is told to skip them by name.
FRAME_LABELS = ("$x$", "$y$", "$O$")


def fmt(value, digits=3):
    """Short numeric label: ``2``, ``-1.5``, ``0.333``.

    Trailing zeros are stripped because a textbook writes ``1.5``, not
    ``1.500``, and the label is read as a value, not as a measurement.
    """
    v = float(value)
    if not math.isfinite(v):
        return ""
    if abs(v - round(v)) < 1e-9:
        return "%d" % int(round(v))
    out = ("%." + str(int(digits)) + "f") % v
    out = out.rstrip("0").rstrip(".")
    return "0" if out in ("-0", "") else out


def frame(ax, xlim, ylim, xlabel="$x$", ylabel="$y$", origin=True,
          style="center", zorder=5):
    """Draw the two axis arrows; return the labels painted.

    ``style="center"`` puts the origin inside the picture -- the shape of a
    parabola or a sine curve is read against the origin, so it must be visible.

    ``style="corner"`` puts the axes on the left and bottom edges, for graphs
    whose origin *is* the corner (``x-t``, ``p-V``, titration).  Drawing a
    centred origin there would put the curve on top of the axis.
    """
    x0, x1 = float(xlim[0]), float(xlim[1])
    y0, y1 = float(ylim[0]), float(ylim[1])
    w, h = x1 - x0, y1 - y0
    painted = []
    arrow_kw = dict(arrowstyle="-|>", color="k", lw=1.2,
                    mutation_scale=11, shrinkA=0, shrinkB=0)

    if style == "corner":
        ax.annotate("", xy=(x1, y0), xytext=(x0, y0), arrowprops=arrow_kw,
                    zorder=zorder)
        ax.annotate("", xy=(x0, y1), xytext=(x0, y0), arrowprops=arrow_kw,
                    zorder=zorder)
        ax.text(x1, y0 - 0.045 * h, xlabel, fontsize=10.5, ha="right", va="top")
        ax.text(x0 - 0.012 * w, y1, ylabel, fontsize=10.5, ha="right", va="top")
        painted += [xlabel, ylabel]
        if origin:
            ax.text(x0 - 0.012 * w, y0 - 0.045 * h, "$O$", fontsize=10,
                    ha="right", va="top")
            painted.append("$O$")
        return painted

    ax.annotate("", xy=(x1 - 0.015 * w, 0), xytext=(x0 + 0.015 * w, 0),
                arrowprops=arrow_kw, zorder=zorder)
    ax.annotate("", xy=(0, y1 - 0.015 * h), xytext=(0, y0 + 0.015 * h),
                arrowprops=arrow_kw, zorder=zorder)
    ax.text(x1 - 0.01 * w, 0.022 * h, xlabel, fontsize=10.5, ha="right",
            va="bottom")
    ax.text(0.014 * w, y1 - 0.01 * h, ylabel, fontsize=10.5, ha="left", va="top")
    painted += [xlabel, ylabel]
    if origin:
        ax.text(-0.012 * w, -0.022 * h, "$O$", fontsize=10, ha="right", va="top")
        painted.append("$O$")
    return painted


def dot(ax, x, y, filled=True, color="k", ms=5.0, zorder=6):
    """A marked point.  Hollow means "not included", filled means "included"."""
    if filled:
        ax.plot(x, y, "o", ms=ms, color=color, zorder=zorder,
                markeredgewidth=0)
    else:
        ax.plot(x, y, "o", ms=ms, color="white", markeredgecolor=color,
                markeredgewidth=1.4, zorder=zorder)


def arrow(ax, p0, p1, color="#1a1a1a", lw=1.6, zorder=6, style="-|>",
          shrink=0.0, scale=12):
    """A single arrow from ``p0`` to ``p1``."""
    ax.annotate("", xy=tuple(p1), xytext=tuple(p0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                shrinkA=shrink, shrinkB=shrink,
                                mutation_scale=scale),
                zorder=zorder)


def bracket(ax, p0, p1, text=None, color="#555", lw=1.1, fontsize=9.5,
            text_off=(0.0, 0.0), ha="center", va="center", zorder=6,
            style="<|-|>"):
    """A double-headed measure between two points, with optional text.

    Used for a period, a wavelength, a chord, a distance -- anything the
    question asks the reader to read off as a length rather than as a value on
    an axis.
    """
    arrow(ax, p0, p1, color=color, lw=lw, zorder=zorder, style=style, scale=10)
    if not text:
        return None
    mx = 0.5 * (p0[0] + p1[0]) + text_off[0]
    my = 0.5 * (p0[1] + p1[1]) + text_off[1]
    return ax.text(mx, my, text, fontsize=fontsize, color=color,
                   ha=ha, va=va, zorder=zorder)


def guide(ax, p0, p1, color="#9e9e9e", lw=1.0, zorder=2, dashes=(4, 3)):
    """A dashed construction line: an asymptote, a projection, an axis of symmetry."""
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], ls=(0, dashes), color=color,
            lw=lw, zorder=zorder)


def ticks(ax, x0, x1, y=0.0, length=0.10, max_count=26):
    """Short tick marks along a horizontal axis; returns the values drawn."""
    lo = int(math.ceil(min(x0, x1) - 1e-9))
    hi = int(math.floor(max(x0, x1) + 1e-9))
    if hi - lo + 1 > max_count:
        return []
    vals = list(range(lo, hi + 1))
    for v in vals:
        ax.plot([v, v], [y - length, y + length], color="#1a1a1a", lw=1.0,
                zorder=3)
    return vals


def finish_panels(fig, axes, out_path, skip=()):
    """``layout.finish`` for a figure with more than one panel.

    ``layout.finish`` audits a single Axes.  A two-panel figure that passes only
    the left one therefore publishes the right panel with no collision check at
    all -- the labels there can overlap freely and the report still says
    ``collisions: 0``.  This resolves every extra panel first and then hands the
    first one to ``layout.finish``, which does the measuring and the saving, so
    the returned report covers every label on the page.
    """
    from .. import layout

    axes = list(axes)
    extra_before, extra_after, extra_moved = [], [], []
    for ax in axes[1:]:
        before, after, moved = layout.resolve(ax, skip=skip)
        extra_before.extend(before)
        extra_after.extend(after)
        extra_moved.extend(moved)

    report = layout.finish(fig, axes[0], out_path, skip=skip)
    report["collisions"] += len(extra_after)
    report["fixed"] += len(extra_moved)
    report["remaining"].extend(
        {"kind": c["kind"], "label": c["a"], "with": c["b"]}
        for c in extra_after)
    return report
