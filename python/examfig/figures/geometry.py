# -*- coding: utf-8 -*-
r"""Triangle with its circumcircle, and a line cutting a circle.

**Triangle.**  A "solve the triangle" question always states three of the six
elements and asks for the rest.  The figure has to show *the triangle the prose
describes*, so the vertices are computed from the given sides -- never placed
by eye -- and every derived angle is printed with the value the drawing
actually used.  The circumcircle is included because the sine rule
``a / sin A = 2R`` is the fact being taught, and ``R`` is only believable if the
circle visibly passes through all three vertices; that is asserted, not
assumed.

Sides are given as ``a, b, c`` with the usual convention: ``a`` is opposite
vertex ``A``, and so on.  Any three sides that satisfy the triangle inequality
work; a set that does not is rejected rather than drawn as a degenerate sliver.

**Line and circle.**  The chord length and the distance from the centre are
linked by ``(d/2)**2 + dist**2 = r**2``; drawing the chord first and the
distance afterwards lets the two disagree by a pixel or two, which is enough to
make a "perpendicular from the centre" look slanted.  Here the foot of the
perpendicular is computed, and the right-angle mark is placed at that foot.
"""
import math

import numpy as np

from .. import env, labelplace, layout
from . import _helpers as H

_C_TRI = "#1a1a1a"
_C_CIRC = "#1565c0"
_C_CHORD = "#c62828"
_C_ALT = "#2e7d32"


def _circumcircle(A, B, C):
    """Centre and radius of the circle through three points."""
    ax_, ay = A
    bx, by = B
    cx, cy = C
    d = 2.0 * (ax_ * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        raise ValueError("the three vertices are collinear; no circumcircle")
    ux = ((ax_ ** 2 + ay ** 2) * (by - cy) + (bx ** 2 + by ** 2) * (cy - ay)
          + (cx ** 2 + cy ** 2) * (ay - by)) / d
    uy = ((ax_ ** 2 + ay ** 2) * (cx - bx) + (bx ** 2 + by ** 2) * (ax_ - cx)
          + (cx ** 2 + cy ** 2) * (bx - ax_)) / d
    centre = np.array([ux, uy])
    r = float(np.linalg.norm(np.array(A) - centre))
    return centre, r


def triangle_solve(a=5.0, b=6.0, c=7.0, show_circle=True, show_angles=True,
                   out_path="math_triangle.png"):
    r"""The triangle with sides ``a, b, c`` and its circumcircle.

    ``a`` is the side opposite ``A``, as usual.  Returns the three angles in
    degrees and the circumradius ``R``.
    """
    plt = env.pyplot()
    a, b, c = float(a), float(b), float(c)
    for name, v in (("a", a), ("b", b), ("c", c)):
        if v <= 0:
            raise ValueError("side %s must be positive (got %g)" % (name, v))
    if a + b <= c or a + c <= b or b + c <= a:
        raise ValueError("sides %g, %g, %g violate the triangle inequality"
                         % (a, b, c))

    # Standard construction: A at the origin, B along +x at distance c, C from
    # the two circles of radius b (about A) and a (about B).
    A = np.array([0.0, 0.0])
    B = np.array([c, 0.0])
    xC = (b * b + c * c - a * a) / (2.0 * c)
    yC2 = b * b - xC * xC
    if yC2 <= 0:
        raise ValueError("sides %g, %g, %g do not close into a triangle"
                         % (a, b, c))
    C = np.array([xC, math.sqrt(yC2)])

    # Angles from the law of cosines -- the same numbers the picture uses.
    Aang = math.degrees(math.acos((b * b + c * c - a * a) / (2 * b * c)))
    Bang = math.degrees(math.acos((a * a + c * c - b * b) / (2 * a * c)))
    Cang = 180.0 - Aang - Bang

    centre, R = _circumcircle(A, B, C)
    for P in (A, B, C):
        assert abs(np.linalg.norm(P - centre) - R) < 1e-9, \
            "circumcircle misses a vertex"

    fig, ax = plt.subplots(figsize=(5.0, 4.4), dpi=300)

    if show_circle:
        t = np.linspace(0, 2 * math.pi, 720)
        ax.plot(centre[0] + R * np.cos(t), centre[1] + R * np.sin(t),
                color=_C_CIRC, lw=1.2, zorder=2)

    for P, Q in ((A, B), (B, C), (C, A)):
        ax.plot([P[0], Q[0]], [P[1], Q[1]], color=_C_TRI, lw=1.9, zorder=5)

    # The frame is set before any label is placed: every offset below is in
    # points, and a point is only a fixed number of data units once the scale
    # is final.  With sides of 1 and 10 in the same figure a data-unit offset
    # that clears the edge in one case sits on the edge in the other.
    allp = np.vstack([A, B, C])
    if show_circle:
        allp = np.vstack([allp, centre - R, centre + R])
    ax.set_xlim(float(allp[:, 0].min()), float(allp[:, 0].max()))
    ax.set_ylim(float(allp[:, 1].min()), float(allp[:, 1].max()))
    ax.set_aspect("equal")
    fig.canvas.draw()
    pad_x = 26.0 / max(H.points_per_unit(ax, fig, axis="x"), 1e-9)
    pad_y = 26.0 / max(H.points_per_unit(ax, fig, axis="y"), 1e-9)
    ax.set_xlim(float(allp[:, 0].min()) - pad_x, float(allp[:, 0].max()) + pad_x)
    ax.set_ylim(float(allp[:, 1].min()) - pad_y, float(allp[:, 1].max()) + pad_y)

    painted = []
    centroid = (A + B + C) / 3.0
    # Every name on this figure is anchored to a point the geometry fixes -- a
    # vertex, a side midpoint, an angle bisector -- but *which side* of that
    # point the glyphs go is not fixed: with sides of 1 and 10 in one triangle
    # there is no single outward direction that stays clear of all three edges.
    # So the anchors are collected here and the placement search picks the spot
    # against the finished geometry.
    anchors = []
    labels = []

    if show_circle:
        H.dot(ax, centre[0], centre[1], filled=True, color=_C_CIRC, ms=3.8)
        anchors.append((float(centre[0]), float(centre[1])))
        labels.append("$O$")

    for name, P in (("A", A), ("B", B), ("C", C)):
        H.dot(ax, P[0], P[1], filled=True, ms=4.4)
        anchors.append((float(P[0]), float(P[1])))
        labels.append("$%s$" % name)
        painted.append(name)

    for name, P, Q, val in (("a", B, C, a), ("b", C, A, b), ("c", A, B, c)):
        mid = 0.5 * (P + Q)
        anchors.append((float(mid[0]), float(mid[1])))
        labels.append("$%s=%s$" % (name, H.fmt(val)))
        painted.append("%s=%s" % (name, H.fmt(val)))

    if show_angles:
        # Each angle is marked at its vertex, inside the wedge, with the
        # computed value -- the reader can then add them up and get 180.  The
        # arc radius is set in points, so a small triangle keeps the arc inside
        # the wedge instead of swallowing it.
        ppu = min(H.points_per_unit(ax, fig, axis="x"),
                  H.points_per_unit(ax, fig, axis="y"))
        rr = 20.0 / max(ppu, 1e-9)
        for name, P, Q, R_, val in (("A", A, B, C, Aang),
                                    ("B", B, A, C, Bang),
                                    ("C", C, A, B, Cang)):
            v1 = (Q - P) / (np.linalg.norm(Q - P) or 1.0)
            v2 = (R_ - P) / (np.linalg.norm(R_ - P) or 1.0)
            ang1 = math.atan2(v1[1], v1[0])
            ang2 = math.atan2(v2[1], v2[0])
            # Sweep the short way round, so the arc stays inside the angle.
            d = ang2 - ang1
            while d > math.pi:
                d -= 2 * math.pi
            while d < -math.pi:
                d += 2 * math.pi
            t = np.linspace(ang1, ang1 + d, 80)
            ax.plot(P[0] + rr * np.cos(t), P[1] + rr * np.sin(t),
                    color="#616161", lw=1.0, zorder=4)
            mid = ang1 + d / 2.0
            anchors.append((float(P[0] + rr * math.cos(mid)),
                            float(P[1] + rr * math.sin(mid))))
            labels.append(r"$%s^{\circ}$" % H.fmt(val, 1))
            painted.append("%s^\\circ" % H.fmt(val, 1))

    if show_circle:
        anchors.append((float(centre[0]), float(centre[1] + R)))
        labels.append("$R=%s$" % H.fmt(R, 2))
        painted.append("R=%s" % H.fmt(R, 2))

    labelplace.place_labels(
        ax, anchors, labels, fontsize=10,
        avoid_segments=layout.obstacles(ax),
        xlim=ax.get_xlim(), ylim=ax.get_ylim())
    H.expand_to_fit(fig, ax, pad_pt=5.0)
    ax.axis("off")
    report = layout.finish(fig, ax, out_path)

    return {
        "angles_deg": {"A": Aang, "B": Bang, "C": Cang},
        "R": float(R),
        "centre": [float(centre[0]), float(centre[1])],
        "marks": set(painted),
        "layout": report,
    }


def circle_line(r=3.0, dist=1.8, angle_deg=0.0, tangent=False,
                out_path="math_circleline.png"):
    r"""A circle and a line at distance ``dist`` from its centre.

    ``tangent=True`` forces ``dist = r`` -- a tangent is the limiting case of a
    chord whose endpoints coincide, and drawing it any other way would show a
    "tangent" that cuts the circle.

    Returns the chord length (``0`` for a tangent) and the perpendicular
    distance actually drawn.
    """
    plt = env.pyplot()
    r = float(r)
    if r <= 0:
        raise ValueError("r must be positive")
    if tangent:
        dist = r
    dist = float(dist)
    if dist > r + 1e-9:
        raise ValueError(
            "distance %g exceeds r = %g: the line misses the circle entirely"
            % (dist, r))

    half_chord = math.sqrt(max(0.0, r * r - dist * dist))
    chord = 2.0 * half_chord
    phi = math.radians(float(angle_deg))

    fig, ax = plt.subplots(figsize=(4.8, 4.3), dpi=300)
    ax.set_aspect("equal")

    painted = []
    lim = r * 1.55
    painted += H.frame(ax, (-lim, lim), (-lim, lim), style="center")

    t = np.linspace(0, 2 * math.pi, 720)
    ax.plot(r * np.cos(t), r * np.sin(t), color=_C_TRI, lw=1.7, zorder=4)

    # Unit vector along the line, and the normal pointing at the centre.
    u = np.array([math.cos(phi), math.sin(phi)])
    n = np.array([-u[1], u[0]])
    foot = n * dist                       # closest point of the line to O
    extent = r * 1.42
    p0 = foot - u * extent
    p1 = foot + u * extent
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=_C_CHORD, lw=1.8, zorder=5)

    H.dot(ax, 0.0, 0.0, filled=True, ms=4.2)
    ax.text(-0.07, -0.07, "$O$", fontsize=10.5, ha="right", va="top")
    painted.append("O")

    # The perpendicular from the centre: dashed, with its length printed.
    H.guide(ax, (0.0, 0.0), (foot[0], foot[1]), color=_C_ALT, lw=1.3)
    if dist > 1e-9:
        # Right-angle mark at the foot, built from the two unit directions.
        sz = 0.16 * r
        m1 = foot + u * sz
        m2 = m1 - n * sz
        m3 = foot - n * sz
        ax.plot([m1[0], m2[0], m3[0]], [m1[1], m2[1], m3[1]],
                color=_C_ALT, lw=1.0, zorder=6)
        mid = foot / 2.0
        ax.text(mid[0] + n[0] * 0.16 * r, mid[1] + n[1] * 0.16 * r,
                "$d=%s$" % H.fmt(dist, 2), fontsize=10, color=_C_ALT,
                ha="center", va="center", zorder=9)
        painted.append("d=%s" % H.fmt(dist, 2))

    if chord > 1e-9:
        # Chord endpoints on the circle, and the chord length as a measure.
        e1 = foot - u * half_chord
        e2 = foot + u * half_chord
        for e, nm in ((e1, "$A$"), (e2, "$B$")):
            H.dot(ax, e[0], e[1], filled=True, color=_C_CHORD, ms=4.6)
            out = e / (np.linalg.norm(e) or 1.0)
            ax.text(e[0] + out[0] * 0.24, e[1] + out[1] * 0.24, nm,
                    fontsize=11, color=_C_CHORD, ha="center", va="center")
        painted += ["A", "B"]
        ax.text(foot[0] - n[0] * 0.26 * r, foot[1] - n[1] * 0.26 * r,
                "$|AB|=%s$" % H.fmt(chord, 2), fontsize=10, color=_C_CHORD,
                ha="center", va="center", zorder=9)
        painted.append("|AB|=%s" % H.fmt(chord, 2))
    else:
        H.dot(ax, foot[0], foot[1], filled=True, color=_C_CHORD, ms=4.6)
        out = foot / (np.linalg.norm(foot) or 1.0)
        ax.text(foot[0] + out[0] * 0.26, foot[1] + out[1] * 0.26, "$A$",
                fontsize=11, color=_C_CHORD, ha="center", va="center")
        painted.append("A")

    ax.text(-lim * 0.92, lim * 0.92, "$r=%s$" % H.fmt(r, 2), fontsize=10,
            ha="left", va="top")
    painted.append("r=%s" % H.fmt(r, 2))

    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.axis("off")
    report = layout.finish(fig, ax, out_path, skip=("$x$", "$y$", "$O$"))

    return {"r": r, "distance": dist, "chord": float(chord),
            "half_chord": float(half_chord), "tangent": bool(tangent),
            "marks": set(painted), "layout": report}


def vectors(u=(3.0, 1.0), v=(1.0, 2.5), mode="both",
            out_path="math_vectors.png"):
    r"""Vector addition: the parallelogram rule and the triangle rule.

    Both rules describe the *same* resultant, and that is the whole lesson, so
    the two panels share one coordinate system and the resultant is drawn once
    as a dashed diagonal -- not twice, which would suggest two answers.

    ``mode`` is ``"both"``, ``"parallelogram"`` or ``"triangle"``.
    """
    plt = env.pyplot()
    mode = str(mode or "both").strip().lower()
    if mode not in ("both", "parallelogram", "triangle"):
        raise ValueError("mode must be both, parallelogram or triangle "
                         "(got %r)" % mode)

    u = np.array([float(u[0]), float(u[1])])
    v = np.array([float(v[0]), float(v[1])])
    w = u + v
    if np.linalg.norm(u) < 1e-9 or np.linalg.norm(v) < 1e-9:
        raise ValueError("both vectors must be non-zero")

    O = np.array([0.0, 0.0])
    pts = np.array([O, u, v, w])
    fig, ax = plt.subplots(figsize=(4.9, 4.3), dpi=300)
    ax.set_aspect("equal")

    lo = pts.min(axis=0) - 0.9
    hi = pts.max(axis=0) + 0.9
    painted = []
    painted += H.frame(ax, (lo[0], hi[0]), (lo[1], hi[1]), style="center")

    _CU, _CV, _CW = "#1565c0", "#2e7d32", "#c62828"

    H.arrow(ax, O, u, color=_CU, lw=1.9, zorder=6)
    H.arrow(ax, O, v, color=_CV, lw=1.9, zorder=6)

    painted += ["u", "v"]
    # u and v labels at the arrow tips, pushed along each arrow's own direction.
    for vec, col, nm in ((u, _CU, "$\\vec{u}$"), (v, _CV, "$\\vec{v}$")):
        tip = O + vec * 1.10
        ax.text(tip[0], tip[1], nm, fontsize=12, color=col, ha="center",
                va="center", zorder=9)

    if mode in ("both", "parallelogram"):
        # The far corner is reached either way; the two "ghost" sides are the
        # parallelogram's other pair of edges.
        H.arrow(ax, u, w, color=_CV, lw=1.2, zorder=4, style="-|>", scale=9)
        H.arrow(ax, v, w, color=_CU, lw=1.2, zorder=4, style="-|>", scale=9)

    if mode in ("both", "triangle"):
        # The triangle rule: v translated to the tip of u, then the resultant
        # closes the triangle.  Drawn from u, not from O, to show the shift.
        H.arrow(ax, u, w, color=_CV, lw=1.6, zorder=5)

    H.arrow(ax, O, w, color=_CW, lw=2.2, zorder=7)
    tip = O + w * 1.09
    ax.text(tip[0], tip[1], "$\\vec{u}+\\vec{v}$", fontsize=11.5,
            color=_CW, ha="center", va="center", zorder=9)
    painted.append("u+v")

    H.dot(ax, *O, filled=True, ms=4.2)
    ax.text(-0.10, -0.10, "$O$", fontsize=10.5, ha="right", va="top")
    painted.append("O")
    H.dot(ax, w[0], w[1], filled=True, color=_CW, ms=4.6)

    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.axis("off")
    report = layout.finish(fig, ax, out_path, skip=("$x$", "$y$", "$O$"))

    return {"sum": [float(w[0]), float(w[1])],
            "norm_sum": float(np.linalg.norm(w)),
            "mode": mode, "marks": set(painted), "layout": report}
