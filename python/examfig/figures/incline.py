# -*- coding: utf-8 -*-
r"""Inclined plane with gravity and its two components.

Four defects here were invisible until the PNG was actually looked at, and each
one shaped the code that remains:

1. **The gravity arrow pierced the ground.**  The block sat at ``0.40L`` while
   the arrow was longer than the block's height above the ground, so ``G``
   crossed the floor line -- physically nonsense.  Fixed by moving the block up
   and keeping ``G`` short enough to leave clearance.

2. **The ``theta`` label sat on top of the ``G\\perp`` arrow.**  The anchor was
   placed outside the arc, right where ``G\\perp`` lands.  Textbooks put the
   angle label *inside* the arc, near the vertex.  That is a deterministic
   rule, so it is written to a fixed offset rather than handed to the
   optimiser.

3. **``labelplace`` ended with ``autoscale_view()``**, which undid the viewport
   that had just been set.  Labels had been positioned against the old
   transform, so every one of them shifted.  :func:`_grow_to_fit` now only
   ever expands.

4. **The optimiser put labels in "whatever space was free"** rather than where
   they belong: ``G`` and ``G\\perp`` both drifted into the same empty corner.
   Non-overlapping is not the same as interpretable.  Force-vector labels
   belong at the arrow tip, pushed along the arrow's own normal -- that is the
   textbook convention, and hard-coding it separates the three arrows for
   free.

The general lesson: **an optimiser decides between candidate positions; it
cannot decide where a label belongs in the first place.**  Anything with a
convention gets the convention.
"""
import numpy as np

from .. import env
from ..labelplace import _overlap, _rect_seg_dist
COL_G = "#c62828"
COL_PAR = "#1565c0"
COL_PERP = "#2e7d32"
COL_BLOCK = "#37474f"


def _grow_to_fit(fig, ax, artists, pad_frac=0.02):
    """Expand the viewport to include ``artists``; never shrink it.

    ``autoscale_view()`` recomputes the window from the data, discarding the
    hand-set limits that every label was positioned against.
    """
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    for t in artists:
        bb = t.get_window_extent(rend)
        (dx0, dy0) = inv.transform((bb.x0, bb.y0))
        (dx1, dy1) = inv.transform((bb.x1, bb.y1))
        x0, x1 = min(x0, dx0), max(x1, dx1)
        y0, y1 = min(y0, dy0), max(y1, dy1)
    px, py = (x1 - x0) * pad_frac, (y1 - y0) * pad_frac
    ax.set_xlim(x0 - px, x1 + px)
    ax.set_ylim(y0 - py, y1 + py)


def _extent(fig, ax, artist):
    """Measured ``(width, height)`` of a text artist, in data coordinates.

    Must be measured: a CJK glyph is more than twice as wide as a mathtext
    subscript, so any character-count estimate is wrong often enough to matter.
    """
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    bb = artist.get_window_extent(rend)
    (x0, y0) = inv.transform((bb.x0, bb.y0))
    (x1, y1) = inv.transform((bb.x1, bb.y1))
    return abs(x1 - x0), abs(y1 - y0)


def _rect(p, w, h):
    return np.array([[p[0] - w / 2, p[1] - h / 2],
                     [p[0] + w / 2, p[1] + h / 2]])


def _box(r):
    """Corner-pair form used by the optimiser in this module -> (x0,y0,x1,y1)."""
    return (min(r[0][0], r[1][0]), min(r[0][1], r[1][1]),
            max(r[0][0], r[1][0]), max(r[0][1], r[1][1]))


def _cost(rect, placed, segs, frame, margin=0.05):
    c = 0.0
    box = _box(rect)
    for pr in placed:
        c += _overlap(box, _box(pr)) * 5000.0
    for k in (0, 1):
        if rect[0][k] < frame[0][k]:
            c += (frame[0][k] - rect[0][k]) ** 2 * 4000.0
        if rect[1][k] > frame[1][k]:
            c += (rect[1][k] - frame[1][k]) ** 2 * 4000.0
    for sg in segs:
        c += max(0.0, margin - _rect_seg_dist(box, sg[0], sg[1])) ** 2 * 900.0
    return c


def _place_arrow_labels(ax, fig, arrows, segs, frame, fontsize=11.5):
    r"""Force labels: anchor at the tip, push along the arrow's own normal."""
    placed, artists = [], []
    for p0, p1, name in arrows:
        a, b = np.asarray(p0, float), np.asarray(p1, float)
        d = b - a
        d = d / (float(np.linalg.norm(d)) + 1e-12)

        probe = ax.text(0, 0, "$%s$" % name, fontsize=fontsize,
                        ha="center", va="center")
        w, h = _extent(fig, ax, probe)
        probe.remove()
        perp = np.array([-d[1], d[0]])
        proj = abs(perp[0]) * w / 2 + abs(perp[1]) * h / 2

        best = None
        for dist in (0.03, 0.10, 0.18, 0.28):
            p = b + perp * (proj + dist)
            r = _rect(p, w, h)
            c = _cost(r, placed, segs, frame) + 8.0 * dist
            if best is None or c < best[0]:
                best = (c, p, r)
        _, p, r = best
        artists.append(ax.text(p[0], p[1], "$%s$" % name, fontsize=fontsize,
                               ha="center", va="center", zorder=20))
        placed.append(r)
    return artists


def incline(theta_deg=30, out_path="phys_incline.png", G=1.55, L=7.2):
    """An inclined plane of angle ``theta_deg`` carrying a block of weight ``G``.

    Returns ``G_par``/``G_perp`` (the two components) alongside the marks.
    """
    plt = env.pyplot()
    th = np.radians(theta_deg)
    fig, ax = plt.subplots(figsize=(5.6, 3.1), dpi=300)

    O = np.array([0.0, 0.0])
    A = np.array([L * np.cos(th), 0.0])       # the angle lives at this vertex
    B = np.array([0.0, L * np.sin(th)])

    for s in [(O, A), (A, B), (B, O)]:
        ax.plot(*zip(*s), "k-", lw=1.9, zorder=2, solid_capstyle="round")

    up_slope = (B - A) / np.linalg.norm(B - A)
    down_slope = -up_slope
    # The outward normal must be orthogonal to the slope.  Writing
    # [-sin, cos] here gives a dot product of 2 sin cos, i.e. a slanted
    # "normal": the G_perp arrow then points the wrong way and the block is
    # drawn as a parallelogram.  (sin, cos) is the correct one, and the
    # assertion keeps it that way.
    n_out = np.array([np.sin(th), np.cos(th)])
    into = -n_out
    assert abs(n_out @ up_slope) < 1e-9, "outward normal is not orthogonal to the slope"

    C0 = A + 0.60 * (B - A)
    bw, bh = 0.42, 0.40
    corners = [C0 - bw * up_slope,
               C0 + bw * up_slope,
               C0 + bw * up_slope + bh * n_out,
               C0 - bw * up_slope + bh * n_out]
    ax.add_patch(env.patches().Polygon(corners, closed=True, facecolor=COL_BLOCK,
                                       edgecolor=COL_BLOCK, lw=1.0, zorder=7))
    blk = C0 + 0.5 * bh * n_out

    # Angle arc; the label goes inside it, near the vertex.
    r = 0.88
    a1, a2 = np.pi - th, np.pi
    arc = np.linspace(a1, a2, 90)
    ax.plot(A[0] + r * np.cos(arc), A[1] + r * np.sin(arc), "k-", lw=1.0, zorder=3)
    a_mid = (a1 + a2) / 2.0
    ax.text(A[0] + 0.56 * r * np.cos(a_mid), A[1] + 0.56 * r * np.sin(a_mid),
            r"$%d^{\circ}$" % theta_deg, fontsize=11.5,
            ha="center", va="center", zorder=8)

    Gl, Gn = G * np.sin(th), G * np.cos(th)
    arrows = [
        ("G", np.array([0.0, -G]), COL_G),
        (r"G_{\parallel}", down_slope * Gl, COL_PAR),
        (r"G_{\perp}", into * Gn, COL_PERP),
    ]

    xs = [O[0], A[0], B[0], blk[0]]
    ys = [O[1], A[1], B[1], blk[1]]
    for _, vec, _ in arrows:
        xs.append(blk[0] + vec[0])
        ys.append(blk[1] + vec[1])
    pad = 0.45
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect("equal")
    ax.axis("off")

    for _, vec, col in arrows:
        ax.annotate("", xy=blk + vec, xytext=blk,
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=1.9,
                                    shrinkA=3, shrinkB=0, mutation_scale=13),
                    zorder=6)

    artists = _place_arrow_labels(
        ax, fig,
        [(tuple(blk), tuple(blk + vec), name) for name, vec, _ in arrows],
        segs=[(tuple(O), tuple(A)), (tuple(A), tuple(B)), (tuple(B), tuple(O))]
             + [(tuple(blk), tuple(blk + vec)) for _, vec, _ in arrows],
        frame=np.array([ax.get_xlim(), ax.get_ylim()]),
    )

    _grow_to_fit(fig, ax, artists)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.savefig(out_path, bbox_inches="tight", pad_inches=0.06, facecolor="white")
    plt.close(fig)

    marks = {"G", r"G_{\parallel}", r"G_{\perp}", "%d^\\circ" % theta_deg}
    return {"G_par": float(Gl), "G_perp": float(Gn),
            "ratio": float(Gl / Gn), "tan": float(np.tan(th)),
            "labels": sorted(marks), "marks": sorted(marks)}
