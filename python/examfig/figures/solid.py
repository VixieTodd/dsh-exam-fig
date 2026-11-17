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

from .. import env, labelplace, layout
from . import _helpers as H


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


def _rect_gap(rect, a, b):
    """Clearance between an axis-aligned rect and a segment (negative = overlap)."""
    x0, y0, x1, y1 = rect
    # Distance from the segment to the rect: sample the segment and the rect
    # corners, which is exact for the rect-vs-segment case that matters here.
    pts = [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]
    best = 1e18
    for p in pts:
        best = min(best, _point_seg(p, a, b))
    for t in np.linspace(0.0, 1.0, 21):
        q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        dx = max(x0 - q[0], 0.0, q[0] - x1)
        dy = max(y0 - q[1], 0.0, q[1] - y1)
        best = min(best, (dx * dx + dy * dy) ** 0.5)
    return best


def _point_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    den = dx * dx + dy * dy
    if den <= 1e-12:
        return float(np.hypot(p[0] - a[0], p[1] - a[1]))
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / den
    t = max(0.0, min(1.0, t))
    return float(np.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy)))


def draw_polyhedron(ax, verts, faces, labels, d, right, upv,
                    hidden_dashes=(3.5, 2.5), lw=1.4, label_off=17.0):
    """Visible edges solid, hidden edges dashed; return the projected points.

    Label placement is a separate step (``place_vertex_labels``) because it has
    to run *after* the viewport is final: a label's size in data units depends
    on the axis scale, so a spot that is clear before the frame is set can be on
    top of an edge afterwards.

    Returns ``(projected_points, edge_flags)``.
    """
    verts = np.asarray(verts, dtype=float)
    P = project(verts, d, right, upv)
    flags = hidden_edge_flags(verts, faces, d)

    for (i, j), is_hidden in flags.items():
        kind = "hidden" if is_hidden else "visible"
        style = (dict(color="k", lw=lw * 0.72, dashes=hidden_dashes)
                 if kind == "hidden"
                 else dict(color="k", lw=lw, solid_capstyle="round"))
        ax.plot([P[i, 0], P[j, 0]], [P[i, 1], P[j, 1]], **style)
    return P, flags


def frame_polyhedron(ax, P, pad_pt=26.0):
    """Frame the projected solid with room for labels outside every vertex.

    The pad is given in points and converted with the *final* scale, so the
    margin is the same physical size whatever the solid's dimensions are.
    """
    fig = ax.figure
    x0, x1 = float(P[:, 0].min()), float(P[:, 0].max())
    y0, y1 = float(P[:, 1].min()), float(P[:, 1].max())
    if x1 - x0 <= 0:
        x1 = x0 + 1.0
    if y1 - y0 <= 0:
        y1 = y0 + 1.0
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ppu_x = H.points_per_unit(ax, fig, axis="x")
    ppu_y = H.points_per_unit(ax, fig, axis="y")
    pad_x = pad_pt / max(ppu_x, 1e-6)
    pad_y = pad_pt / max(ppu_y, 1e-6)
    ax.set_xlim(x0 - pad_x, x1 + pad_x)
    ax.set_ylim(y0 - pad_y, y1 + pad_y)


def place_vertex_labels(ax, P, flags, labels, label_off=17.0, artists=None):
    """Write the vertex names clear of the edges that meet them.

    Every candidate direction and distance is scored against the edges actually
    drawn, with the label's own measured box -- a single outward bisector is not
    enough: on a tall pyramid the back-left vertex's bisector runs into the
    near-vertical edge from the front vertex to the apex.

    The scoring depends on the scale, and growing the frame afterwards changes
    it: a label keeps its point offset while its box grows in data units, so a
    slot that cleared the edges by 0.033 units is touching them once the frame
    widens.  ``artists`` therefore lets the caller run this again against the
    final scale without stacking a second set of labels on the first.

    Returns ``(painted, artists)``.
    """
    fig = ax.figure
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    axes_bb = ax.get_window_extent(rend)
    px_per_pt = fig.dpi / 72.0
    sx = abs(ax.get_xlim()[1] - ax.get_xlim()[0]) / max(axes_bb.width, 1.0)
    sy = abs(ax.get_ylim()[1] - ax.get_ylim()[0]) / max(axes_bb.height, 1.0)

    neighbours = {i: set() for i in labels}
    for face in flags:
        pass
    for i in neighbours:
        for j in neighbours:
            if i != j and (i, j) in flags or (j, i) in flags:
                neighbours[i].add(j)

    segs = [(P[i], P[j]) for (i, j) in flags]

    artists = dict(artists or {})
    painted = []
    for idx, name in labels.items():
        away = np.zeros(2)
        for j in neighbours.get(idx, ()):
            w = P[j] - P[idx]
            n = np.linalg.norm(w)
            if n > 1e-9:
                away -= w / n
        n = np.linalg.norm(away)
        if n < 1e-9:
            away = P[idx] - P.mean(axis=0)
            n = np.linalg.norm(away)
        if n < 1e-9:
            away = np.array([0.0, 1.0])
            n = 1.0
        base_dir = away / n

        artist = artists.get(idx)
        if artist is None:
            artist = ax.annotate(name, xy=(P[idx, 0], P[idx, 1]),
                                 xytext=(base_dir[0] * label_off,
                                         base_dir[1] * label_off),
                                 textcoords="offset points", fontsize=11,
                                 ha="center", va="center")
            artists[idx] = artist
        else:
            artist.xy = (P[idx, 0], P[idx, 1])
        fig.canvas.draw()
        bb = artist.get_window_extent(rend)
        half_w = (bb.width / 2.0) * sx
        half_h = (bb.height / 2.0) * sy

        best, best_gap = None, -1e9
        for ang in range(0, 360, 20):
            ca, sa = np.cos(np.radians(ang)), np.sin(np.radians(ang))
            # The search has to clear the same margin the audit enforces, or it
            # returns a slot the audit then reports: at a = 0.3 the cube is
            # only 0.42 data units across, so a 0.02-unit gap looks wide to a
            # maximiser and is still inside layout.LINE_MARGIN.
            for dist in (label_off, label_off * 1.5, label_off * 2.2,
                         label_off * 3.0):
                cx = P[idx, 0] + ca * dist * px_per_pt * sx
                cy = P[idx, 1] + sa * dist * px_per_pt * sy
                rect = (cx - half_w, cy - half_h, cx + half_w, cy + half_h)
                gap = min(_rect_gap(rect, s[0], s[1]) for s in segs)
                # A slot inside the audit's margin is not a candidate at all: the
                # maximiser used to return the widest slot even when every slot
                # was touching, and the audit then reported what the search had
                # just chosen.
                if gap < layout.LINE_MARGIN:
                    gap -= 10.0
                # Prefer the bisector direction when it is clear anyway, so the
                # label stays where a reader expects it.
                gap -= 0.05 * ((ca - base_dir[0]) ** 2 + (sa - base_dir[1]) ** 2)
                if gap > best_gap:
                    best_gap, best = gap, (ca * dist, sa * dist)
        artist.set_position(best)
        painted.append(name.strip("$"))
    return painted, artists


def _settle_vertex_labels(ax, P, flags, labels, rounds=5):
    """Place the vertex names and grow the frame until both stop moving.

    Placement is scored against the current scale and framing changes that
    scale, so a single pass can leave a label touching an edge it cleared a
    moment earlier.  Two passes are not enough either -- the frame only stops
    growing once the boxes fit, and the boxes only stop moving once the frame
    stops growing -- so this repeats until a pass changes neither.
    """
    artists, painted = None, []
    prev = None
    for _ in range(rounds):
        painted, artists = place_vertex_labels(ax, P, flags, labels,
                                               artists=artists)
        fitted = H.expand_to_fit(fig=ax.figure, ax=ax, pad_pt=4.0)
        now = tuple(round(v, 3) for i in sorted(artists)
                    for v in artists[i].get_position())
        if fitted and now == prev:
            break
        prev = now
    return painted, artists


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
    P, flags = draw_polyhedron(ax, v, faces, labels, d, right, upv)

    if show_diagonal:
        ax.plot([P[0, 0], P[6, 0]], [P[0, 1], P[6, 1]], color="#c62828",
                lw=1.5, alpha=0.95)
        # The diagonal is not labelled on the figure -- there is no room for a
        # string between two vertices -- so it is not a mark.  ``figcheck``
        # would then fail a stem that asks about AC1, which is the honest
        # outcome: the picture shows the segment, not the name.
    # Frame first, then place: a label's size in data units depends on the
    # scale, so placement before the frame is a placement at the wrong scale.
    frame_polyhedron(ax, P)
    # Place, grow the frame to hold the boxes that were written, and place
    # again: ``expand_to_fit`` changes the data-unit size of a fixed-point label,
    # so the first placement was scored at a scale that no longer holds.
    artists, painted = _settle_vertex_labels(ax, P, flags, labels)
    report = layout.finish(fig, ax, out_path)

    # Vertices are tuples; subtract only after converting, or Python raises
    # "unsupported operand type(s) for -: 'tuple' and 'tuple'".
    diag = float(np.linalg.norm(np.asarray(v[6]) - np.asarray(v[0])))
    return {"diagonal": diag, "marks": set(painted), "layout": report}


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
    P, flags = draw_polyhedron(ax, v, faces, labels, d, right, upv)

    O = project([(0, 0, 0)], d, right, upv)[0]
    ax.plot([P[4, 0], O[0]], [P[4, 1], O[1]], color="k", lw=0.9,
            dashes=(3.5, 2.5))
    frame_polyhedron(ax, P)
    painted, _artists = _settle_vertex_labels(ax, P, flags, labels)
    # The foot of the height sits inside the base, between the height line and
    # the near base edge; where a label fits there depends on the base's width,
    # so the search finds a clear slot rather than a fixed offset that only
    # works for one aspect ratio.  It runs last, against the final scale.
    labelplace.place_labels(
        ax, [(float(O[0]), float(O[1]))], ["$O$"], fontsize=10,
        avoid_segments=layout.obstacles(ax),
        xlim=ax.get_xlim(), ylim=ax.get_ylim())
    painted.append("O")
    report = layout.finish(fig, ax, out_path)
    return {"height": float(h), "marks": set(painted), "layout": report}
