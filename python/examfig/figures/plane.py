# -*- coding: utf-8 -*-
r"""Plane geometry: parabola and right triangle.

Both functions derive every coordinate from the parameters the question uses,
so the picture cannot disagree with the numbers in the prose.
"""
import numpy as np

from .. import env


def quadratic(a, b, c, out_path="math_quadratic.png"):
    r"""``y = a x^2 + b x + c``: vertex, roots and axis of symmetry from (a,b,c).

    Three layout rules, each learned from a rendered page:

    1. **Do not set the upper limit to ``vertex_y + constant``.**  With the
       vertex at y = -4 that leaves 0.2 units above the x-axis, so the axis
       rides the top border and the root labels fall outside the frame.  Use
       ``max(0, vertex_y) + margin`` so there is always room above the axis.
    2. **Put root labels *below* the axis.**  A parabola opens upward on both
       sides of a root, so anything above it gets crossed by the curve.
    3. **No equal aspect.**  With y spanning 8 units and x spanning 5, equal
       scaling turns the plot into a tall sliver.  Textbook parabola sketches
       are vertically compressed on purpose.
    """
    plt = env.pyplot()
    vx = -b / (2.0 * a)
    vy = a * vx ** 2 + b * vx + c
    disc = b * b - 4 * a * c
    roots = ([] if disc < 0
             else [(-b - disc ** 0.5) / (2 * a), (-b + disc ** 0.5) / (2 * a)])

    fig, ax = plt.subplots(figsize=(4.2, 3.3), dpi=300)

    y_lo = vy - 1.3
    y_hi = max(0.0, vy) + 2.3
    x_lo, x_hi = vx - 2.9, vx + 2.9
    if roots:                          # never let a root fall outside the frame
        x_lo = min(x_lo, min(roots) - 0.55)
        x_hi = max(x_hi, max(roots) + 0.55)

    xs = np.linspace(x_lo, x_hi, 900)
    ys = a * xs ** 2 + b * xs + c
    m = (ys >= y_lo) & (ys <= y_hi)     # clip, or the curve is cut mid-stroke
    ax.plot(xs[m], ys[m], color="#1a1a1a", lw=2.0, zorder=3)

    ax.annotate("", xy=(x_hi - 0.12, 0), xytext=(x_lo + 0.10, 0),
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.2), zorder=2)
    ax.annotate("", xy=(0, y_hi - 0.18), xytext=(0, y_lo + 0.16),
                arrowprops=dict(arrowstyle="-|>", color="k", lw=1.2), zorder=2)
    ax.text(x_hi - 0.06, 0.16, "$x$", fontsize=10, ha="right", va="bottom")
    ax.text(0.12, y_hi - 0.12, "$y$", fontsize=10, ha="left", va="top")
    ax.text(-0.16, -0.10, "$O$", fontsize=10, ha="right", va="top")

    ax.plot([vx, vx], [vy, y_hi - 0.55], ls=(0, (4, 3)), color="#999",
            lw=1.1, zorder=1)
    ax.text(vx + 0.14, y_hi - 0.62, "$x=%g$" % vx, fontsize=9, color="#555",
            ha="left", va="top")

    # Root labels go *outside* the parabola, below the axis.  Directly below a
    # root is inside the region the descending branch sweeps through, so the
    # text has to be pushed away from the vertex as well: ha="right" for the
    # left root, ha="left" for the right one.
    lo_root, hi_root = (min(roots), max(roots)) if roots else (None, None)
    for r in roots:
        ax.plot(r, 0, "o", ms=4.5, color="k", zorder=4)
        outside_left = (r == lo_root)
        ax.text(r - 0.10 if outside_left else r + 0.10, -0.22, "%g" % r,
                fontsize=10, ha="right" if outside_left else "left",
                va="top")

    ax.plot(vx, vy, "o", ms=5, color="k", zorder=4)
    ax.text(vx + 0.16, vy - 0.16, "(%g, %g)" % (vx, vy), fontsize=10,
            ha="left", va="top")

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    marks = {"O", "x", "y", "%g" % vx, "%g" % vy} | {"%g" % r for r in roots}
    return {"vertex": (vx, vy), "roots": roots, "marks": marks}


def triangle(ac, bc, out_path="math_triangle.png"):
    r"""Right triangle ``ABC`` with the right angle at ``C``, ``AC=ac``, ``BC=bc``.

    An earlier version put the right angle at ``A`` and swapped the identities
    of the two legs.  The picture looked plausible, which is exactly what made
    it dangerous: a student reading ``angle C`` off the figure would find an
    acute angle.  The fourth-level check caught it because the drawing
    function's ``marks`` said ``right_angle_at: A``.

    Vertices are now pinned by the statement: ``C`` at the origin, ``CA`` along
    +x of length ``ac``, ``CB`` along +y of length ``bc``.  There is then no
    freedom left for the right-angle mark to land anywhere but ``C``.
    """
    plt = env.pyplot()
    ab = (ac * ac + bc * bc) ** 0.5          # from Pythagoras, not measured

    fig, ax = plt.subplots(figsize=(3.6, 3.0), dpi=300)
    ax.set_aspect("equal")

    C = np.array([0.0, 0.0])
    A = np.array([float(ac), 0.0])
    B = np.array([0.0, float(bc)])

    for p, q in ((A, B), (B, C), (C, A)):
        ax.plot(*zip(p, q), "k-", lw=1.5)

    s = min(ac, bc) * 0.14
    ax.plot(*zip(C + [s, 0], C + [s, s], C + [0, s]), "k-", lw=1.0)

    for p, name, off in ((C, "$C$", (-0.26, -0.24)),
                         (A, "$A$", (0.14, -0.14)),
                         (B, "$B$", (-0.10, 0.16))):
        ax.plot(*p, "k.", ms=3.5)
        ax.text(p[0] + off[0], p[1] + off[1], name, fontsize=10)

    ax.text(ac / 2.0, -0.24, "%g" % ac, fontsize=10, ha="center")
    ax.text(-0.26, bc / 2.0, "%g" % bc, fontsize=10, va="center", ha="right")
    ax.text(ac / 2.0 + 0.20, bc / 2.0 + 0.16, "%g" % ab, fontsize=10)

    ax.set_xlim(-0.55, ac + 0.45)
    ax.set_ylim(-0.55, bc + 0.45)
    ax.axis("off")
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    return {"hypotenuse": ab, "right_angle_at": "C",
            "marks": {"A", "B", "C", "%g" % ac, "%g" % bc, "%g" % ab, "90"}}
