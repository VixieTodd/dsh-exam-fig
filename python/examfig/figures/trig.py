# -*- coding: utf-8 -*-
r"""Trigonometric curve ``y = A sin(omega x + phi) + shift``.

The figure answers exactly four questions and nothing else:

* **与 y 轴的交点** -- the point where the curve meets the y-axis, marked with a
  dot and its value.
* **最大值 / 最小值** -- the two horizontal guides, each with its value on the
  y-axis, plus the extremum dots on the curve.
* **周期** -- a bracket between two *corresponding* points (peak to peak).

Deliberately absent: the function expression (the paper states it in the prose,
and repeating it invites the two to disagree) and the midline (``平衡位置``) --
neither is asked for, and both add strokes that labels then have to dodge.

Two layout rules, both from the textbook:

* The period is measured peak to peak, not between zero crossings: zero
  crossings sit where the curve meets the midline, and a bracket there would
  collide with the very stroke it measures.
* The y tick labels sit left of the axis.  They are what the range question is
  answered from, so they must be legible on their own.
"""
import math

import numpy as np

from .. import env, layout

_TWO_PI = 2.0 * math.pi

# sin(k*pi/den) for the denominators that appear in textbook angles, as
# (coefficient, radicand): the value is coefficient * sqrt(radicand).
_SIN_TABLE = {
    (1, 1): (0.0, 1), (2, 1): (1.0, 1),
    (1, 2): (1.0, 1), (3, 2): (-1.0, 1),
    (1, 3): (0.5, 3), (2, 3): (0.5, 3), (4, 3): (-0.5, 3), (5, 3): (-0.5, 3),
    (1, 4): (0.5, 2), (3, 4): (0.5, 2), (5, 4): (-0.5, 2), (7, 4): (-0.5, 2),
    (1, 6): (0.5, 1), (5, 6): (0.5, 1), (7, 6): (-0.5, 1), (11, 6): (-0.5, 1),
}


def _fmt_frac(value):
    r"""LaTeX for a small rational: ``1``, ``-\frac{1}{2}``, ``\frac{3}{2}``."""
    for den in (1, 2, 3, 4, 6):
        scaled = value * den
        if abs(scaled - round(scaled)) < 1e-9:
            num = int(round(scaled))
            if den == 1:
                return "%d" % num
            sign = "-" if num < 0 else ""
            return r"%s\frac{%d}{%d}" % (sign, abs(num), den)
    return "%g" % value


def _fmt_pi(value):
    r"""LaTeX for a multiple of ``pi``: ``\pi``, ``\frac{\pi}{2}``, ``2\pi``."""
    if abs(value) < 1e-12:
        return "0"
    ratio = value / math.pi
    for den in (1, 2, 3, 4, 6):
        num = ratio * den
        if abs(num - round(num)) < 1e-9:
            num = int(round(num))
            if den == 1:
                return r"\pi" if num == 1 else (r"-\pi" if num == -1 else r"%d\pi" % num)
            body = "" if abs(num) == 1 else str(abs(num))
            sign = "-" if num < 0 else ""
            return r"%s\frac{%s\pi}{%d}" % (sign, body, den)
    return "%g\\pi" % ratio


def _sin_exact(phi):
    """Exact ``sin(phi)`` as ``(coefficient, radicand)``, or ``None``."""
    for den in (1, 2, 3, 4, 6):
        k = phi * den / math.pi
        if abs(k - round(k)) < 1e-9:
            key = (int(round(k)) % (2 * den), den)
            if key in _SIN_TABLE:
                return _SIN_TABLE[key]
    return None


def _fmt_y0(shift, A, phi):
    r"""Exact ``A sin(phi) + shift`` when it is a textbook form, else 3 digits.

    ``1+\sqrt{3}`` is the answer a student is expected to write; ``2.73`` is
    only a check.  The exact form is preferred whenever the angle is a
    multiple of pi/6, pi/4 or pi/3.
    """
    exact = _sin_exact(phi)
    if exact is not None:
        coef, rad = exact
        t = A * coef
        if rad == 1:
            return _fmt_frac(shift + t)
        if abs(t) > 1e-12:
            head = _fmt_frac(shift) if abs(shift) > 1e-12 else ""
            body = _fmt_frac(abs(t)) if abs(abs(t) - 1.0) > 1e-12 else ""
            sign = "-" if t < 0 else "+"
            if not head:
                sign = "-" if t < 0 else ""
            return r"%s%s%s\sqrt{%d}" % (head, sign, body, rad)
        return _fmt_frac(shift)
    return "%.3g" % (A * math.sin(phi) + shift)


def trig(A=1.0, omega=1.0, phi=0.0, shift=0.0, periods=1.0,
         out_path="math_trig.png"):
    r"""Plot one sine wave, marking the y-intercept, extrema and period."""
    plt = env.pyplot()
    A = float(A)
    omega = float(omega)
    phi = float(phi)
    shift = float(shift)
    periods = max(0.5, float(periods))
    if abs(omega) < 1e-12:
        raise ValueError("omega must be non-zero")

    period = _TWO_PI / abs(omega)
    # Anchor the window on a peak: the left edge is then exactly a trough, so
    # the reader sees a whole shape instead of a fragment.
    x_peak = (math.pi / 2.0 - phi) / omega
    x_lo = x_peak - 0.5 * period - 0.18
    x_hi = x_peak + periods * period + 0.18
    # The y-axis must be inside the frame: the intercept is one of the four
    # things the figure is asked to show.
    x_lo = min(x_lo, -0.18)
    x_hi = max(x_hi, 0.18)

    amp = abs(A)
    y_lo = shift - amp - 0.80
    y_hi = shift + amp + 1.15          # headroom for the period bracket

    fig, ax = plt.subplots(figsize=(5.4, 3.5), dpi=300)

    xs = np.linspace(x_lo, x_hi, 1600)
    ys = A * np.sin(omega * xs + phi) + shift
    ax.plot(xs, ys, color="#1a1a1a", lw=2.0, zorder=4,
            solid_capstyle="round")

    # The two extremes: dashed guides carrying the max and min values.  They
    # start just right of the y-axis, not at the frame edge: a guide drawn
    # through the tick-label column makes every value label sit "on a line",
    # and the de-overlap pass then lifts it off its own row, which is worse
    # than the collision it repairs.
    for yv in (shift + amp, shift - amp):
        ax.plot([0.06, x_hi], [yv, yv], ls=(0, (5, 3)), color="#b0b0b0",
                lw=1.0, zorder=1)
        ax.plot([-0.06, 0.04], [yv, yv], color="#1a1a1a", lw=1.0, zorder=3)

    ax.annotate("", xy=(x_hi - 0.10, 0), xytext=(x_lo + 0.06, 0),
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.2), zorder=5)
    ax.annotate("", xy=(0, y_hi - 0.14), xytext=(0, y_lo + 0.12),
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.2), zorder=5)

    ax.text(x_hi - 0.04, 0.16, "$x$", fontsize=10.5, ha="right", va="bottom")
    ax.text(0.14, y_hi - 0.10, "$y$", fontsize=10.5, ha="left", va="top")
    ax.text(0.13, -0.22, "$O$", fontsize=10.5, ha="left", va="top")

    # Max and min only -- the midline value is not asked for.
    for yv in (shift + amp, shift - amp):
        ax.text(-0.12, yv, "%g" % yv, fontsize=9.5, ha="right", va="center")

    # Extremum dots.
    for k in range(-2, int(periods) + 3):
        xp = x_peak + k * period
        if x_lo <= xp <= x_hi:
            ax.plot(xp, shift + A, "o", ms=4.6, color="#c0392b", zorder=6)
        xt = xp + 0.5 * period
        if x_lo <= xt <= x_hi:
            ax.plot(xt, shift - A, "o", ms=4.6, color="#1f6feb", zorder=6)

    # Period bracket, peak to peak, above everything the curve touches.
    y_bar = shift + amp + 0.55
    x0, x1 = x_peak, x_peak + period
    if x1 > x_hi:
        x1 = x_hi - 0.05
    ax.annotate("", xy=(x1, y_bar), xytext=(x0, y_bar),
                arrowprops=dict(arrowstyle="<|-|>", color="#555", lw=1.1),
                zorder=6)
    for xv in (x0, x1):
        ax.plot([xv, xv], [y_bar - 0.10, shift + amp + 0.08], ls=(0, (2, 2)),
                color="#888", lw=0.9, zorder=2)
    ax.text((x0 + x1) / 2.0, y_bar + 0.08,
            "$T=%s$" % _fmt_pi(period), fontsize=9.5, color="#333",
            ha="center", va="bottom")

    # y-intercept: the dot and its value, placed below-right of the point.
    y0 = A * math.sin(phi) + shift
    ax.plot(0, y0, "o", ms=4.6, color="#1e8449", zorder=7)
    ax.text(0.10, y0 - 0.14, "$%s$" % _fmt_y0(shift, A, phi),
            fontsize=9.5, color="#1e8449", ha="left", va="top", zorder=7)

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    # The three axis names are meant to sit on the strokes they name.
    report = layout.finish(fig, ax, out_path, skip=("$O$", "$x$", "$y$"))

    marks = {"O", "x", "y",
             "%g" % (shift + amp), "%g" % (shift - amp),
             "T=%s" % _fmt_pi(period),
             "y0=%s" % _fmt_y0(shift, A, phi)}
    return {"amplitude": amp, "period": period, "midline": shift,
            "y_intercept": y0,
            "extrema": [[shift + amp, "max"], [shift - amp, "min"]],
            "marks": marks, "layout": report}
