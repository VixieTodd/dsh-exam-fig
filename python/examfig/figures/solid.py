# -*- coding: utf-8 -*-
r"""Solid geometry: let the program decide which edges are hidden.

The first attempt failed for three reasons worth remembering:

1. **Wrong convention.**  It treated ``ABCD`` as the *front* face and
   ``A1B1C1D1`` as the back.  Chinese textbooks take ``ABCD`` as the **base**
   and ``A1B1C1D1`` as the **top**, with ``AA1``... as vertical edges.  Get the
   naming wrong and nothing else can be right.
2. **Hard-coded dashes.**  Which edges are hidden depends on the camera, so a
   hard-coded list breaks the moment the viewpoint changes.
3. **Unicode subscripts.**  ``A₁`` (U+2081) has no glyph in many CJK fonts and
   renders as a box.  Labels here are always mathtext: ``$A_1$``.

The correct approach for any convex polyhedron is orthographic projection plus
back-face culling: **an edge is hidden when both of its incident faces face
away from the camera.**  For a convex solid that is necessary and sufficient,
so no ray casting is needed.
"""
import numpy as np

from .. import env


def camera(azimuth_deg, elev_deg):
    """Orthographic camera basis projecting world coordinates to screen (u, v).

    Right-handed: x right, y away, z up.  ``azimuth`` spins about z,
    ``elev`` tilts up.
    """
    a, e = np.radians(azimuth_deg), np.radians(elev_deg)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    d = d / np.linalg.norm(d)
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(up, d)
    right = right / np.linalg.norm(right)
    upv = np.cross(d, right)
    return d, right, upv


def project(pts, d, right, upv):
    pts = np.asarray(pts, dtype=float)
    return np.column_stack([pts @ right, pts @ upv])


def hidden_edge_flags(verts, faces, d):
    """``{(i, j): is_hidden}`` for a convex polyhedron."""
    verts = np.asarray(verts, dtype=float)
    front = []
    for f in faces:
        p0, p1, p2 = verts[f[0]], verts[f[1]], verts[f[2]]
        n = np.cross(p1 - p0, p2 - p0)
        front.append(np.dot(n, d) < 0)   # normal toward the camera => visible

    edge_faces = {}
    for fi, f in enumerate(faces):
        for i in range(len(f)):
            e = tuple(sorted((f[i], f[(i + 1) % len(f)])))
            edge_faces.setdefault(e, []).append(fi)

    return {e: not any(front[fi] for fi in fs) for e, fs in edge_faces.items()}


def draw_polyhedron(ax, verts, faces, labels, d, right, upv,
                    hidden_dashes=(3.5, 2.5), lw=1.4, label_off=0.10):
    """Visible edges solid, hidden edges dashed, vertex labels pushed outward."""
    verts = np.asarray(verts, dtype=float)
    P = project(verts, d, right, upv)
    flags = hidden_edge_flags(verts, faces, d)

    for (i, j), is_hidden in flags.items():
        kind = "hidden" if is_hidden else "visible"
        style = (dict(color="k", lw=lw * 0.72, dashes=hidden_dashes)
                 if kind == "hidden"
                 else dict(color="k", lw=lw, solid_capstyle="round"))
        ax.plot([P[i, 0], P[j, 0]], [P[i, 1], P[j, 1]], **style)

    center = P.mean(axis=0)
    for idx, name in labels.items():
        v = P[idx] - center
        n = np.linalg.norm(v)
        if n < 1e-9:
            continue
        v = v / n
        ax.text(P[idx, 0] + v[0] * label_off, P[idx, 1] + v[1] * label_off,
                name, fontsize=11, ha="center", va="center")
    return P


def cube_geometry(a=1.0):
    """Base ``ABCD`` at z=0, top ``A1B1C1D1`` at z=a -- the textbook naming."""
    v = [
        (0, 0, 0), (a, 0, 0), (a, a, 0), (0, a, 0),
        (0, 0, a), (a, 0, a), (a, a, a), (0, a, a),
    ]
    faces = [
        (0, 1, 2, 3),        # base
        (4, 5, 6, 7),        # top
        (0, 1, 5, 4),        # front ABB1A1
        (1, 2, 6, 5),        # right BCC1B1
        (2, 3, 7, 6),        # back
        (3, 0, 4, 7),        # left
    ]
    labels = {0: "$A$", 1: "$B$", 2: "$C$", 3: "$D$",
              4: "$A_1$", 5: "$B_1$", 6: "$C_1$", 7: "$D_1$"}
    return v, faces, labels


def cube(out_path="math_cube.png", a=1.0, show_diagonal=True):
    """A cube, optionally with body diagonal ``AC1`` highlighted."""
    plt = env.pyplot()
    v, faces, labels = cube_geometry(a)
    fig, ax = plt.subplots(figsize=(4.0, 3.8), dpi=300)
    ax.set_aspect("equal")
    ax.axis("off")

    d, right, upv = camera(azimuth_deg=-55, elev_deg=22)
    P = draw_polyhedron(ax, v, faces, labels, d, right, upv)

    if show_diagonal:
        ax.plot([P[0, 0], P[6, 0]], [P[0, 1], P[6, 1]], color="#c62828",
                lw=1.5, alpha=0.95)

    ax.autoscale_view()
    ax.margins(0.16)
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # Vertices are tuples; subtract only after converting, or Python raises
    # "unsupported operand type(s) for -: 'tuple' and 'tuple'".
    diag = float(np.linalg.norm(np.asarray(v[6]) - np.asarray(v[0])))
    marks = {"A", "B", "C", "D", "A_1", "B_1", "C_1", "D_1"}
    if show_diagonal:
        marks.add("AC_1")
    return {"diagonal": diag, "marks": marks}


def pyramid(out_path="math_pyramid.png", a=1.0, h=1.05):
    """Right square pyramid ``P-ABCD`` with its height ``PO`` dashed."""
    plt = env.pyplot()
    v = [
        (-a / 2, -a / 2, 0), (a / 2, -a / 2, 0),
        (a / 2, a / 2, 0), (-a / 2, a / 2, 0),
        (0, 0, h),
    ]
    faces = [(0, 1, 2, 3), (0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
    labels = {0: "$A$", 1: "$B$", 2: "$C$", 3: "$D$", 4: "$P$"}

    fig, ax = plt.subplots(figsize=(4.0, 3.6), dpi=300)
    ax.set_aspect("equal")
    ax.axis("off")
    d, right, upv = camera(azimuth_deg=-60, elev_deg=20)
    P = draw_polyhedron(ax, v, faces, labels, d, right, upv)

    O = project([(0, 0, 0)], d, right, upv)[0]
    ax.plot([P[4, 0], O[0]], [P[4, 1], O[1]], color="k", lw=0.9,
            dashes=(3.5, 2.5))
    ax.text(O[0] + 0.06, O[1] - 0.10, "$O$", fontsize=10,
            ha="center", va="center")
    ax.autoscale_view()
    ax.margins(0.18)
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return {"height": float(h), "marks": {"A", "B", "C", "D", "P", "O"}}
