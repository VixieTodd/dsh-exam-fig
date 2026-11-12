# -*- coding: utf-8 -*-
r"""Power functions ``y = x^a`` for several exponents on one pair of axes.

The five exponents of the textbook figure are 1, 2, 3, -1 and 1/2.  Drawing
them together is what makes the family visible: every one of them passes
through ``(1, 1)``, the odd ones are odd functions, and the sign of the
exponent decides which side of that point the curve rises.

Two domain facts drive the code and are easy to get wrong:

* ``x^(1/2)`` is only real for ``x >= 0`` -- plotting the negative side anyway
  gives a straight line of NaNs that matplotlib silently drops, which looks
  like a curve that "starts at the origin" instead of one that is undefined.
* ``x^(-1)`` blows up at the origin, so a naive ``linspace`` puts astronomically
  large values in the array and destroys the autoscaled view.

Both are handled by building the sample set per exponent and clipping to the
frame, never by letting the plotter guess.
"""
import numpy as np

from .. import env, layout

# Chosen so that five curves stay distinguishable in print and each label can
# be coloured to match the curve it names.
_PALETTE = ["#1a1a1a", "#c0392b", "#1f6feb", "#7d3c98", "#1e8449",
            "#b9770e", "#0e6655"]


def _fmt_exp(a):
    r"""LaTeX body for the exponent: ``1``, ``-1``, ``1/2``, ``3``."""
    a = float(a)
    if a == int(a):
        return "%d" % int(a)
    if abs(a - 0.5) < 1e-12:
        return "1/2"
    if abs(a + 0.5) < 1e-12:
        return "-1/2"
    return ("%g" % a)


def power(exponents=(1.0, 2.0, 3.0, -1.0, 0.5), out_path="math_power.png"):
    r"""Plot ``y = x^a`` for every exponent in ``exponents``.

    The legend sits in the fourth quadrant because that quadrant is empty for
    every real power function of a positive number: all five curves stay at
    ``y > 0`` for ``x > 0``.  Putting the legend anywhere else would make it
    cover the very curves it describes.
    """
    plt = env.pyplot()
    exps = [float(a) for a in exponents]
    if not exps:
        raise ValueError("exponents must not be empty")

    x_lo, x_hi = -3.1, 3.3
    y_lo, y_hi = -3.2, 3.2

    fig, ax = plt.subplots(figsize=(4.6, 4.4), dpi=300)
    ax.set_aspect("auto")

    handles, labels = [], []
    for i, a in enumerate(exps):
        colour = _PALETTE[i % len(_PALETTE)]

        xs = np.linspace(x_lo, x_hi, 2400)
        # A non-integer exponent has no real value on the negative side, and a
        # negative exponent has no value at the origin.  Restrict the sample
        # set instead of relying on NaN masking: a masked array still autoscales.
        if not float(a).is_integer():
            xs = xs[xs >= 0.0]
        if a < 0:
            xs = xs[np.abs(xs) > 1e-6]

        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            ys = np.power(xs, a)

        keep = np.isfinite(ys) & (ys >= y_lo) & (ys <= y_hi) & (xs >= x_lo) & (xs <= x_hi)
        handle, = ax.plot(xs[keep], ys[keep], color=colour, lw=2.0, zorder=3,
                          solid_capstyle="round")
        handles.append(handle)
        labels.append("$y=x^{%s}$" % _fmt_exp(a))

    # Axes as arrows, drawn over the curves so the frame reads as a coordinate
    # system rather than as another curve.
    ax.annotate("", xy=(x_hi - 0.12, 0), xytext=(x_lo + 0.08, 0),
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.2), zorder=4)
    ax.annotate("", xy=(0, y_hi - 0.12), xytext=(0, y_lo + 0.10),
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.2), zorder=4)

    # The common point: every positive power sends 1 to 1.  Dashed guides turn
    # that fact into something the reader can check off the axes.
    ax.plot([1, 1], [0, 1], ls=(0, (3, 3)), color="#888", lw=0.9, zorder=2)
    ax.plot([0, 1], [1, 1], ls=(0, (3, 3)), color="#888", lw=0.9, zorder=2)
    ax.plot(1, 1, "o", ms=4.0, color="k", zorder=6)

    ax.text(1.0, -0.14, "$1$", fontsize=9.5, ha="center", va="top")
    ax.text(-0.10, 1.0, "$1$", fontsize=9.5, ha="right", va="center")
    # Every label position near the origin is contested by some curve.  The
    # strip just *below* the x-axis and just *right* of the y-axis is the one
    # genuinely empty region: for 0 < x < 1/3.2 the curve x^-1 is already above
    # the frame, and every other power is above the axis on that side.  That
    # is where `O` goes -- close to the crossing, and not on top of anything.
    ax.text(0.12, -0.16, "$O$", fontsize=10, ha="left", va="top")
    ax.text(x_hi - 0.04, 0.14, "$x$", fontsize=10, ha="right", va="bottom")
    ax.text(0.12, y_hi - 0.06, "$y$", fontsize=10, ha="left", va="top")

    legend = ax.legend(handles, labels, loc="lower right",
                       fontsize=9.5, frameon=True, framealpha=1.0,
                       edgecolor="#999999", borderpad=0.55,
                       labelspacing=0.38, handlelength=1.7,
                       handletextpad=0.6)
    legend.set_zorder(7)
    for text in legend.get_texts():
        text.set_color("#000000")

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    # `O`, `x`, `y` and the two `1` ticks name the axes they sit on; the audit
    # would only ever report them as touching strokes they are meant to touch.
    report = layout.finish(fig, ax, out_path,
                           skip=("$O$", "$x$", "$y$", "$1$"))

    marks = {"O", "x", "y", "1"} | {"y=x^{%s}" % _fmt_exp(a) for a in exps}
    return {"exponents": exps, "common_point": [1.0, 1.0],
            "marks": marks, "layout": report}
