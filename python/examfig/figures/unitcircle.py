# -*- coding: utf-8 -*-
r"""Unit circle with the sine, cosine and tangent lines.

Every textbook definition of the trigonometric functions is a *statement about
three segments*::

    sin(theta) = MP      (the vertical drop from P to the x-axis)
    cos(theta) = OM      (the horizontal run from O to the foot)
    tan(theta) = AT      (the tangent segment from A = (1, 0) to T)

so the figure is only useful if those three segments are drawn *and* their
endpoints are labelled the same way the prose labels them.  They are therefore
computed from ``theta`` and painted explicitly; nothing is inferred from the
rendered image.

The tangent line has its own trap.  ``AT`` exists only while the terminal side
meets the tangent at ``x = 1``; at ``theta = 90`` degrees the terminal side is
*parallel* to it and there is no ``T``.  Rather than draw a wrong segment, the
tangent is omitted once ``|cos theta|`` is below a threshold, and the returned
``tan`` is ``None`` -- the figure and the numbers stay consistent.
"""
import math

import numpy as np

from .. import env, layout
from . import _helpers as H

_C_SIN = "#c62828"
_C_COS = "#1565c0"
_C_TAN = "#2e7d32"
_C_ARM = "#1a1a1a"


def unitcircle(theta_deg=50.0, show_tan=True, show_angles=True,
               out_path="math_unitcircle.png"):
    """The unit circle at angle ``theta_deg`` with the three trig segments.

    Returns ``sin``, ``cos`` and ``tan`` (``None`` when the terminal side is
    parallel to the tangent line).
    """
    plt = env.pyplot()
    th = math.radians(float(theta_deg))
    c, s = math.cos(th), math.sin(th)

    fig, ax = plt.subplots(figsize=(4.7, 4.5), dpi=300)
    ax.set_aspect("equal")

    painted = []
    painted += H.frame(ax, (-1.45, 1.75), (-1.35, 1.35), xlabel="$x$",
                       ylabel="$y$", style="center")

    # The circle itself.
    ang = np.linspace(0, 2 * math.pi, 720)
    ax.plot(np.cos(ang), np.sin(ang), color="#1a1a1a", lw=1.6, zorder=4)

    P = (c, s)
    M = (c, 0.0)          # foot of the perpendicular -- the cosine end
    A = (1.0, 0.0)        # tangent point on the circle

    # Terminal side OP.
    ax.plot([0, c], [0, s], color=_C_ARM, lw=1.7, zorder=5)

    # sin = MP, cos = OM.  Drawn as thick coloured segments so they read as
    # lengths, with the label at the midpoint pushed off the segment.
    ax.plot([c, c], [0, s], color=_C_SIN, lw=2.6, zorder=6)
    ax.plot([0, c], [0, 0], color=_C_COS, lw=2.6, zorder=6)
    ax.text(c - 0.07, s / 2.0, r"$\sin\theta$", fontsize=10.5, color=_C_SIN,
            ha="right", va="center", zorder=9)
    painted.append("sin")
    ax.text(c / 2.0, 0.10, r"$\cos\theta$", fontsize=10.5, color=_C_COS,
            ha="center", va="bottom", zorder=9)
    painted.append("cos")

    # Points and their names.
    H.dot(ax, 0.0, 0.0, filled=True, ms=4.2)
    ax.text(-0.06, -0.06, "$O$", fontsize=10.5, ha="right", va="top")
    painted.append("O")
    H.dot(ax, *P, filled=True, color=_C_SIN, ms=5.0)
    ax.text(c + 0.10, s + 0.06, "$P$", fontsize=11, ha="left", va="bottom")
    painted.append("P")
    H.dot(ax, *M, filled=True, ms=4.0)
    ax.text(c - 0.04, -0.10, "$M$", fontsize=10.5, ha="right", va="top")
    painted.append("M")

    # The angle arc, drawn inside the wedge so it cannot be read as a side.
    arc_r = 0.30
    arc = np.linspace(0, th, 120)
    ax.plot(arc_r * np.cos(arc), arc_r * np.sin(arc), color="#1a1a1a", lw=1.1,
            zorder=6)
    if show_angles:
        mid = th / 2.0
        ax.text(arc_r * 1.42 * math.cos(mid), arc_r * 1.42 * math.sin(mid),
                r"$\theta$", fontsize=11, ha="center", va="center", zorder=9)
        painted.append("theta")

    tan_val = None
    if show_tan and abs(c) > 0.12:
        # T is where the terminal side meets the tangent line x = 1.
        t_y = s / c
        T = (1.0, t_y)
        tan_val = t_y
        # Only draw when T is inside the window; otherwise the segment would
        # leave the figure and its label would be clipped.
        if abs(t_y) <= 1.30:
            H.dot(ax, *A, filled=True, ms=4.0)
            ax.text(1.0, -0.10, "$A$", fontsize=10.5, ha="center", va="top")
            painted.append("A")
            ax.plot([1.0, 1.0], [0.0, t_y], color=_C_TAN, lw=2.6, zorder=6)
            # Dotted continuation of the terminal side to T, so the reader sees
            # *why* AT is the tangent of the same angle.
            ax.plot([c, 1.0], [s, t_y], color="#9e9e9e", lw=0.9,
                    ls=(0, (3, 3)), zorder=3)
            H.dot(ax, *T, filled=True, color=_C_TAN, ms=5.0)
            side = "left" if c > 0 else "right"
            dx = -0.09 if c > 0 else 0.09
            ax.text(1.0 + dx, t_y + 0.05, "$T$", fontsize=11,
                    ha="right" if c > 0 else "left", va="bottom")
            painted.append("T")
            ax.text(1.10, t_y / 2.0, r"$\tan\theta$", fontsize=10.5,
                    color=_C_TAN, ha="left", va="center", zorder=9)
            painted.append("tan")

    ax.set_xlim(-1.45, 1.75)
    ax.set_ylim(-1.35, 1.35)
    ax.axis("off")
    report = layout.finish(fig, ax, out_path, skip=("$x$", "$y$", "$O$"))

    return {
        "theta_deg": float(theta_deg),
        "sin": float(s), "cos": float(c),
        "tan": None if tan_val is None else float(tan_val),
        "marks": set(painted),
        "layout": report,
    }
