# -*- coding: utf-8 -*-
r"""Wave pictures: a travelling wave, a vibration graph, and a standing wave.

The three share one idea and must not share one drawing, because they are read
differently:

* ``wave`` -- ``y`` against ``x`` at one instant.  The wavelength is measured
  between two *adjacent crests*, and the bracket is drawn above the crests.
* ``vibration`` -- ``y`` against ``t`` at one point.  The period is measured
  between two adjacent crests, and the label is ``T``, not ``lambda``.
* ``standing`` -- the envelope is the sum of two opposite waves.  Nodes are
  where the displacement is *always* zero, so they are marked on the axis and
  named ``N``; antinodes get ``A``.

A common defect these avoid: labelling the wavelength on a ``y-t`` graph.  The
two axes differ, so a reader who trusts the label computes the wrong wave
speed.  Each function only ever writes its own quantity.
"""
import math

import numpy as np

from .. import env
from . import _helpers as H

_CURVE = "#1565c0"
_CREST = "#c62828"


def _fmt_pi(value):
    r"""LaTeX for a multiple of pi, e.g. ``2\pi`` or ``\frac{\pi}{2}``."""
    if abs(value) < 1e-12:
        return "0"
    ratio = value / math.pi
    for den in (1, 2, 3, 4, 6):
        num = ratio * den
        if abs(num - round(num)) < 1e-9:
            num = int(round(num))
            if den == 1:
                return r"\pi" if num == 1 else (
                    r"-\pi" if num == -1 else r"%d\pi" % num)
            body = "" if abs(num) == 1 else str(abs(num))
            sign = "-" if num < 0 else ""
            return r"%s\frac{%s\pi}{%d}" % (sign, body, den)
    return "%g\\pi" % ratio


def wave(amplitude=2.0, wavelength=4.0, cycles=2.0, speed=None,
         out_path="phys_wave.png"):
    r"""A snapshot of a travelling wave: ``y`` against ``x``.

    The wavelength bracket runs crest to crest, and the amplitude is marked from
    the axis to the first crest.  If ``speed`` is given the period is computed
    and returned, but it is *not* painted here -- a ``y-x`` graph cannot show a
    period, and painting it is the error this function exists to prevent.
    """
    plt = env.pyplot()
    A = float(amplitude)
    lam = float(wavelength)
    if A <= 0 or lam <= 0:
        raise ValueError("amplitude and wavelength must be positive")
    cycles = max(1.0, float(cycles))
    k = 2.0 * math.pi / lam

    x_lo = -0.08 * lam
    x_hi = cycles * lam + 0.10 * lam
    y_lo, y_hi = -A - 0.55 * A, A + 0.85 * A

    fig, ax = plt.subplots(figsize=(5.6, 3.2), dpi=300)
    xs = np.linspace(x_lo, x_hi, 1400)
    ax.plot(xs, A * np.sin(k * xs), color=_CURVE, lw=2.0, zorder=4)

    painted = H.frame(ax, (x_lo, x_hi), (y_lo, y_hi), xlabel="$x$",
                      ylabel="$y$", style="center")

    # Crests and troughs, as dots.  The first crest is at lambda/4.
    crests = [lam / 4.0 + n * lam for n in range(0, int(cycles) + 2)]
    crests = [c for c in crests if x_lo < c < x_hi]
    for c in crests:
        H.dot(ax, c, A, filled=True, color=_CREST, ms=4.2)
    for c in crests:
        H.dot(ax, c + lam / 2.0, -A, filled=True, color=_CREST, ms=4.2)

    # Amplitude: a double arrow from the axis up to the first crest, drawn just
    # left of that crest so it does not sit on the curve's slope.
    xa = crests[0] - 0.10 * lam if crests else lam / 4.0
    H.bracket(ax, (xa, 0.0), (xa, A), color="#37474f", lw=1.0)
    ax.text(xa - 0.02 * lam, A / 2.0, "$A=%s$" % H.fmt(A, 2), fontsize=9.5,
            color="#37474f", ha="right", va="center")
    painted.append("A=%s" % H.fmt(A, 2))

    # Wavelength: crest to crest, above everything.
    if len(crests) >= 2:
        c0, c1 = crests[0], crests[1]
        y_bar = A + 0.45 * A
        H.bracket(ax, (c0, y_bar), (c1, y_bar), color="#555", lw=1.1)
        for xv in (c0, c1):
            H.guide(ax, (xv, A + 0.05 * A), (xv, y_bar), color="#888")
        ax.text(0.5 * (c0 + c1), y_bar + 0.06 * A,
                r"$\lambda=%s$" % H.fmt(lam, 3), fontsize=9.5, color="#333",
                ha="center", va="bottom")
        painted.append("lambda=%s" % H.fmt(lam, 3))

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    report = H.finish_panels(fig, [ax], out_path,
                             skip=("$x$", "$y$", "$O$"))

    result = {"amplitude": A, "wavelength": lam, "wave_number": k,
              "marks": set(painted), "layout": report}
    if speed:
        speed = float(speed)
        result["period"] = lam / speed
        result["frequency"] = speed / lam
    return result


def vibration(amplitude=2.0, period=0.8, cycles=2.5, out_path="phys_vibration.png"):
    r"""A point's displacement against time: ``y`` against ``t``.

    The period bracket runs crest to crest and is labelled ``T``; the amplitude
    is marked from the axis to a crest.  Nothing here claims a wavelength.
    """
    plt = env.pyplot()
    A = float(amplitude)
    T = float(period)
    if A <= 0 or T <= 0:
        raise ValueError("amplitude and period must be positive")
    cycles = max(1.0, float(cycles))
    omega = 2.0 * math.pi / T

    t_lo = -0.06 * T
    t_hi = cycles * T + 0.10 * T
    y_lo, y_hi = -A - 0.55 * A, A + 0.85 * A

    fig, ax = plt.subplots(figsize=(5.6, 3.2), dpi=300)
    ts = np.linspace(t_lo, t_hi, 1400)
    ax.plot(ts, A * np.sin(omega * ts), color=_CURVE, lw=2.0, zorder=4)

    painted = H.frame(ax, (t_lo, t_hi), (y_lo, y_hi), xlabel="$t$",
                      ylabel="$y$", style="center")

    crests = [T / 4.0 + n * T for n in range(0, int(cycles) + 2)]
    crests = [c for c in crests if t_lo < c < t_hi]
    for c in crests:
        H.dot(ax, c, A, filled=True, color=_CREST, ms=4.2)
        H.dot(ax, c + T / 2.0, -A, filled=True, color=_CREST, ms=4.2)

    # The amplitude bracket stands in the margin left of t = 0, where the sine
    # is *below* the axis, so the upper half of that strip is empty.  Placing it
    # beside the first crest instead means threading the gap between the
    # bracket and the rising stretch of the curve, and that gap is a fraction
    # of a period wide: under a pixel at T = 0.15 s, hundreds of pixels at
    # T = 3 s.  A margin measured in points is the same width for every period.
    ta = -0.16 * T
    H.bracket(ax, (ta, 0.0), (ta, A), color="#37474f", lw=1.0)
    H.offset_text(ax, (ta, A / 2.0), "$A=%s$" % H.fmt(A, 2), dx_pt=-5.0,
                  fontsize=9.5, color="#37474f", ha="right", va="center")
    painted.append("A=%s" % H.fmt(A, 2))

    if len(crests) >= 2:
        c0, c1 = crests[0], crests[1]
        y_bar = A + 0.45 * A
        H.bracket(ax, (c0, y_bar), (c1, y_bar), color="#555", lw=1.1)
        for tv in (c0, c1):
            H.guide(ax, (tv, A + 0.05 * A), (tv, y_bar), color="#888")
        ax.text(0.5 * (c0 + c1), y_bar + 0.06 * A,
                "$T=%s$" % H.fmt(T, 3), fontsize=9.5, color="#333",
                ha="center", va="bottom")
        painted.append("T=%s" % H.fmt(T, 3))

    ax.set_xlim(t_lo, t_hi)
    ax.set_ylim(y_lo, y_hi)
    # The label sits a fixed number of points left of the bracket, which is a
    # different number of data units for every period, so the margin is
    # measured after the scale is final and the axis is widened to fit it.
    fig.canvas.draw()
    ppu = H.points_per_unit(ax, fig, axis="x")
    need = ta - 52.0 / max(ppu, 1e-9)
    if need < t_lo:
        t_lo = need
        ax.set_xlim(t_lo, t_hi)
    ax.axis("off")
    report = H.finish_panels(fig, [ax], out_path,
                             skip=("$t$", "$y$", "$O$"))

    return {"amplitude": A, "period": T, "frequency": 1.0 / T,
            "marks": set(painted), "layout": report}


def standing(amplitude=2.0, length=6.0, antinodes=3, show_envelope=True,
             out_path="phys_standing.png"):
    r"""A standing wave on a string fixed at both ends.

    ``antinodes`` is how many half-wavelengths fit between the two fixed ends --
    the harmonic number.  Nodes are at multiples of ``length/antinodes`` and are
    marked with a dot and ``N``; antinodes sit halfway between and are marked
    ``A``.  The wavelength is ``2*length/antinodes`` and is returned, not
    painted: the picture already shows it as the distance between alternate
    nodes, and a bracket there collides with the nodes it measures.
    """
    plt = env.pyplot()
    A = float(amplitude)
    L = float(length)
    n = int(antinodes)
    if A <= 0 or L <= 0:
        raise ValueError("amplitude and length must be positive")
    if n < 1:
        raise ValueError("antinodes must be at least 1")

    lam = 2.0 * L / n
    k = 2.0 * math.pi / lam
    omega = 1.0

    x_lo, x_hi = -0.10 * L, 1.10 * L
    y_lo, y_hi = -A - 0.45 * A, A + 0.45 * A

    fig, ax = plt.subplots(figsize=(5.8, 3.0), dpi=300)

    xs = np.linspace(0.0, L, 1200)
    painted = []

    if show_envelope:
        env_hi = A * np.abs(np.sin(k * xs))
        ax.plot(xs, env_hi, ls=(0, (5, 3)), color="#b0b0b0", lw=1.0, zorder=2)
        ax.plot(xs, -env_hi, ls=(0, (5, 3)), color="#b0b0b0", lw=1.0, zorder=2)

    # Two snapshots a third of a period apart: the string is drawn where it
    # actually is at those instants, which is what makes the nodes read as
    # fixed.  The second instant is *not* a quarter period later -- at a quarter
    # period the string lies flat on the axis, so the second curve is a straight
    # line on top of the x-axis and shows nothing.
    for phase, lw, colour in ((0.0, 2.0, _CURVE),
                              (math.pi / 3.0, 1.4, "#6f9fd0")):
        ys = A * np.sin(k * xs) * math.cos(phase)
        ax.plot(xs, ys, color=colour, lw=lw, zorder=4)

    # The wall the string is tied to, at both ends.
    for xv in (0.0, L):
        ax.plot([xv, xv], [y_lo + 0.25 * A, y_hi - 0.25 * A], color="#1a1a1a",
                lw=2.4, zorder=5)

    painted.extend(H.frame(ax, (x_lo, x_hi), (y_lo, y_hi), xlabel="$x$",
                           ylabel="$y$", style="corner"))

    # Nodes: equally spaced, including both ends.
    node_xs = [i * L / n for i in range(n + 1)]
    for xv in node_xs:
        H.dot(ax, xv, 0.0, filled=True, color="#1a1a1a", ms=4.0)
    for i, xv in enumerate(node_xs):
        ax.text(xv, -0.16 * A, "$N$", fontsize=9.5, ha="center", va="top",
                color="#1a1a1a")
    painted.append("N")

    # Antinodes: halfway between adjacent nodes.
    anti_xs = [(i + 0.5) * L / n for i in range(n)]
    for xv in anti_xs:
        H.dot(ax, xv, A, filled=True, color=_CREST, ms=4.2)
        H.dot(ax, xv, -A, filled=True, color=_CREST, ms=4.2)
    if anti_xs:
        ax.text(anti_xs[0], A + 0.12 * A, "$A$", fontsize=9.5, ha="center",
                va="bottom", color=_CREST)
        painted.append("A")

    ax.text(L / 2.0, y_hi - 0.06 * A,
            r"$L=%s$" % H.fmt(L, 3), fontsize=9.5, ha="center", va="top",
            color="#455a64")
    painted.append("L=%s" % H.fmt(L, 3))

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    report = H.finish_panels(fig, [ax], out_path,
                             skip=("$x$", "$y$", "$O$", "$N$", "$A$"))

    return {"antinodes": n, "nodes": n + 1, "wavelength": lam,
            "amplitude": A, "length": L,
            "node_positions": node_xs, "antinode_positions": anti_xs,
            "marks": set(painted), "layout": report}
