# -*- coding: utf-8 -*-
"""Put a label near a point without colliding with anything else.

The naive approach -- nudge ``ha``/``va`` by hand until it looks right -- fails
for a structural reason: fixing one label moves the collision onto another,
and there is no way to see the trade-off except by rendering.  This module
makes the choice explicit and searchable.

Given an anchor point and the text to draw, it enumerates the eight compass
directions at two distances, measures the *real* rendered box of each
candidate with the active renderer, and picks the cheapest one:

    cost = out-of-frame  +  label/label overlap  +  label/segment collision
         +  distance from the anchor  +  direction preference

Three rules earned the hard way:

* **Measure, do not estimate.**  A Chinese glyph is roughly twice as wide as a
  mathtext subscript; any width estimate based on character count is wrong
  often enough to matter.
* **Rectangles, not distances.**  Comparing a box to a segment via
  "centre distance minus half-diagonal" badly overestimates clearance for long
  flat boxes and pushes labels off the canvas.  Use true rect-to-segment
  distance.
* **This is for point annotations only.**  Labels anchored to a whole element
  (a resistor, a slope) belong on the outside of that element, at a
  deterministic offset -- see the note in :mod:`examfig.figures.circuit`.
"""
import math

ANGLES = (0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0)
DISTANCES = (0.42, 0.72)

W_FRAME = 3000.0
W_OVERLAP = 4000.0
W_SEGMENT = 900.0
W_ANCHOR = 26.0
W_PREF = 0.010


def _bbox_in_data(ax, text_artist, renderer):
    """Rendered extent of a text artist, converted back to data coordinates."""
    bb = text_artist.get_window_extent(renderer)
    inv = ax.transData.inverted()
    (x0, y0), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _area(rect):
    x0, y0, x1, y1 = rect
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _overlap(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if (w > 0 and h > 0) else 0.0


def _point_in_rect(rect, p, eps=0.0):
    return (rect[0] - eps <= p[0] <= rect[2] + eps
            and rect[1] - eps <= p[1] <= rect[3] + eps)


def _seg_dist(p, a, b):
    """Distance from point ``p`` to segment ``ab``."""
    ax_, ay_ = a
    bx, by = b
    dx, dy = bx - ax_, by - ay_
    den = dx * dx + dy * dy
    if den <= 1e-12:
        return math.hypot(p[0] - ax_, p[1] - ay_)
    t = ((p[0] - ax_) * dx + (p[1] - ay_) * dy) / den
    t = max(0.0, min(1.0, t))
    return math.hypot(p[0] - (ax_ + t * dx), p[1] - (ay_ + t * dy))


def _seg_hits_rect(a, b, rect):
    """True when segment ``ab`` intersects the axis-aligned box."""
    x0, y0, x1, y1 = rect
    if _point_in_rect(rect, a) or _point_in_rect(rect, b):
        return True

    def _inside_interior(px, py):
        return x0 < px < x1 and y0 < py < y1

    if _inside_interior(a[0], a[1]) or _inside_interior(b[0], b[1]):
        return True

    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    for i in range(4):
        if _segments_cross(a, b, corners[i], corners[(i + 1) % 4]):
            return True
    return False


def _segments_cross(p1, p2, p3, p4):
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(v) < 1e-12:
            return 0
        return 1 if v > 0 else -1

    def on_seg(a, b, c):
        return (min(a[0], b[0]) - 1e-12 <= c[0] <= max(a[0], b[0]) + 1e-12
                and min(a[1], b[1]) - 1e-12 <= c[1] <= max(a[1], b[1]) + 1e-12)

    o1 = orient(p1, p2, p3)
    o2 = orient(p1, p2, p4)
    o3 = orient(p3, p4, p1)
    o4 = orient(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and on_seg(p1, p2, p3):
        return True
    if o2 == 0 and on_seg(p1, p2, p4):
        return True
    if o3 == 0 and on_seg(p3, p4, p1):
        return True
    if o4 == 0 and on_seg(p3, p4, p2):
        return True
    return False


def _rect_seg_dist(rect, a, b):
    """True distance between a box and a segment; 0 when they intersect."""
    if _seg_hits_rect(a, b, rect):
        return 0.0
    x0, y0, x1, y1 = rect
    d = min(_seg_dist(a, (x0, y0), (x1, y0)), _seg_dist(b, (x0, y0), (x1, y0)),
            _seg_dist(a, (x1, y0), (x1, y1)), _seg_dist(b, (x1, y0), (x1, y1)),
            _seg_dist(a, (x1, y1), (x0, y1)), _seg_dist(b, (x1, y1), (x0, y1)),
            _seg_dist(a, (x0, y1), (x0, y0)), _seg_dist(b, (x0, y1), (x0, y0)))
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    for c in corners:
        d = min(d, _seg_dist(c, a, b))
    return d


def _cost(rect, frame, taken, segments, anchor, dist, dir_index):
    cost = 0.0
    if frame is not None:
        fx0, fy0, fx1, fy1 = frame
        out = (max(0.0, fx0 - rect[0]) + max(0.0, rect[2] - fx1)
               + max(0.0, fy0 - rect[1]) + max(0.0, rect[3] - fy1))
        cost += W_FRAME * out * out
    for other in taken:
        cost += W_OVERLAP * _overlap(rect, other)
    for seg in segments:
        d = _rect_seg_dist(rect, seg[0], seg[1])
        if d < 0.04:
            cost += W_SEGMENT * (0.04 - d) ** 2
    cx = 0.5 * (rect[0] + rect[2])
    cy = 0.5 * (rect[1] + rect[3])
    gap = math.hypot(cx - anchor[0], cy - anchor[1])
    cost += W_ANCHOR * max(0.0, gap - 0.06) ** 2
    cost += W_PREF * (dist + 0.003 * (dir_index - 1) ** 2)
    return cost


def place_labels(ax, anchors, texts, fontsize=11.0, avoid_segments=(),
                 xlim=None, ylim=None, radii=None):
    """Place ``texts`` near ``anchors`` and return ``(positions, artists)``.

    Parameters
    ----------
    anchors
        One ``(x, y)`` per label, in data coordinates.
    texts
        Mathtext strings, e.g. ``r"$G_{\\parallel}$"``.  Pass the dollars --
        without them matplotlib prints the backslashes literally.
    avoid_segments
        ``[((x0, y0), (x1, y1)), ...]`` lines the labels should not sit on.
    xlim, ylim
        The final viewport.  Pass it explicitly: the canvas must already be
        set to its final size before anything is measured, otherwise the
        data-to-pixel mapping changes after the fact and every label lands
        somewhere else.
    """
    fig = ax.figure
    fig.canvas.draw()
    renderer = fig.get_renderer()

    if xlim is None:
        xlim = ax.get_xlim()
    if ylim is None:
        ylim = ax.get_ylim()
    frame = (xlim[0], ylim[0], xlim[1], ylim[1])
    span = max(1e-9, frame[2] - frame[0])
    taken = []
    out = []
    artists = []

    for i, (anchor, text) in enumerate(zip(anchors, texts)):
        probe = ax.text(anchor[0], anchor[1], text, fontsize=fontsize,
                        ha="center", va="center", alpha=0.0)
        fig.canvas.draw()
        w, h = 0.0, 0.0
        bb = _bbox_in_data(ax, probe, renderer)
        w, h = bb[2] - bb[0], bb[3] - bb[1]
        probe.remove()
        if w <= 0 or h <= 0:
            w, h = 0.06 * span, 0.05 * span

        base = radii[i] if radii else max(0.10, 0.62 * math.hypot(w, h))
        best = None
        for di, angle in enumerate(ANGLES):
            rad = math.radians(angle)
            for dist in DISTANCES:
                r = max(dist * base, 0.52 * math.hypot(w, h))
                cx = anchor[0] + r * math.cos(rad)
                cy = anchor[1] + r * math.sin(rad)
                rect = (cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0)
                c = _cost(rect, frame, taken, avoid_segments, anchor, dist, di)
                if best is None or c < best[0]:
                    best = (c, cx, cy, angle, rect)
        c, cx, cy, angle, rect = best
        taken.append(rect)
        out.append((cx, cy))

        # Horizontal alignment follows the side of the anchor the label ended
        # up on, so the box grows away from the anchor instead of over it.
        ha = "left" if cx > anchor[0] + 1e-9 else ("right" if cx < anchor[0] - 1e-9 else "center")
        va = "bottom" if cy > anchor[1] + 1e-9 else ("top" if cy < anchor[1] - 1e-9 else "center")
        artists.append(ax.text(cx, cy, text, fontsize=fontsize, ha=ha, va=va))

    return out, artists
