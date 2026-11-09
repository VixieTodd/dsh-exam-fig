# -*- coding: utf-8 -*-
"""Collision detection and automatic de-overlapping for figure labels.

Every figure in this package is built from numbers, so the *geometry* is right
by construction.  What goes wrong is the typography: two labels land on top of
each other, a label sits on the curve it describes, or a label drifts outside
the canvas and ``bbox_inches="tight"`` then stretches the saved image into a
nearly blank page.  None of that is visible in the source, and only some of it
is visible on a casual look at the rendered PNG.

This module closes the loop.  After a figure has drawn everything, but before
it is saved, :func:`finish` measures each text's *real* rendered box, finds the
collisions, and tries to nudge the offending labels apart.  It then saves and
returns a report that travels back through the tool layer, so a caller can see
``collisions: 0`` or read what could not be fixed.

Three rules, all learned by getting them wrong:

* **Measure with the renderer.**  ``Text.get_window_extent`` after a canvas
  draw, converted back through ``ax.transData.inverted()``.  Estimating from
  character count is off by roughly 2x between a CJK glyph and a mathtext
  subscript, which is the difference between "clear" and "on top of".
* **The viewport must already be final.**  Any ``set_xlim`` after measuring
  changes the data-to-pixel mapping and every measured box becomes stale, so
  labels that were placed to miss each other start overlapping again.
* **Report, do not hide.**  A repair that cannot find a clear spot must leave
  the label where it was and say so.  Silently returning a figure with a
  collision is how a wrong figure reaches a student.
"""
import math

# A label is "colliding" when it overlaps another label's box, crosses a drawn
# line, or pokes outside the axes limits.  These are separate severities: two
# labels on top of each other makes both unreadable, whereas a label on a thin
# guide line is merely ugly.
SEV_OVERLAP = "overlap"
SEV_LINE = "line"
SEV_FRAME = "frame"

# How much of a line a label is allowed to touch before it counts.  Zero would
# fire on antialiasing-level grazing; a fifth of a millimetre at print size is
# a reasonable "touching".
LINE_MARGIN = 0.03

# Candidate displacements for a repair, in fractions of the label's own size.
_NUDGE = (
    (0.0, 0.0),
    (0.0, 0.6), (0.0, -0.6), (0.6, 0.0), (-0.6, 0.0),
    (0.5, 0.5), (-0.5, 0.5), (0.5, -0.5), (-0.5, -0.5),
    (0.0, 1.2), (0.0, -1.2), (1.2, 0.0), (-1.2, 0.0),
    (1.0, 1.0), (-1.0, 1.0), (1.0, -1.0), (-1.0, -1.0),
)


def _rect_of(artist, ax, renderer):
    """Rendered box of a text artist, in data coordinates."""
    bb = artist.get_window_extent(renderer)
    inv = ax.transData.inverted()
    (x0, y0), (x1, y1) = inv.transform([[bb.x0, bb.y0], [bb.x1, bb.y1]])
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _overlap_area(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if (w > 0 and h > 0) else 0.0


def _point_in(rect, p, eps=0.0):
    return (rect[0] - eps <= p[0] <= rect[2] + eps
            and rect[1] - eps <= p[1] <= rect[3] + eps)


def _point_seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    den = dx * dx + dy * dy
    if den <= 1e-12:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / den
    t = max(0.0, min(1.0, t))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _cross(p1, p2, p3, p4):
    """True when segments p1p2 and p3p4 cross or touch."""
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-12 else (1 if v > 0 else -1)

    def on_seg(a, b, c):
        return (min(a[0], b[0]) - 1e-12 <= c[0] <= max(a[0], b[0]) + 1e-12
                and min(a[1], b[1]) - 1e-12 <= c[1] <= max(a[1], b[1]) + 1e-12)

    o1, o2 = orient(p1, p2, p3), orient(p1, p2, p4)
    o3, o4 = orient(p3, p4, p1), orient(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    return ((o1 == 0 and on_seg(p1, p2, p3)) or (o2 == 0 and on_seg(p1, p2, p4))
            or (o3 == 0 and on_seg(p3, p4, p1)) or (o4 == 0 and on_seg(p3, p4, p2)))


def _seg_hits_rect(a, b, rect):
    if _point_in(rect, a) or _point_in(rect, b):
        return True
    x0, y0, x1, y1 = rect
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    for i in range(4):
        if _cross(a, b, corners[i], corners[(i + 1) % 4]):
            return True
    return False


def _rect_seg_dist(rect, a, b):
    """Distance between a box and a segment; 0 when they intersect."""
    if _seg_hits_rect(a, b, rect):
        return 0.0
    x0, y0, x1, y1 = rect
    d = min(_point_seg_dist(a, (x0, y0), (x1, y0)), _point_seg_dist(b, (x0, y0), (x1, y0)),
            _point_seg_dist(a, (x1, y0), (x1, y1)), _point_seg_dist(b, (x1, y0), (x1, y1)),
            _point_seg_dist(a, (x1, y1), (x0, y1)), _point_seg_dist(b, (x1, y1), (x0, y1)),
            _point_seg_dist(a, (x0, y1), (x0, y0)), _point_seg_dist(b, (x0, y1), (x0, y0)))
    for c in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        d = min(d, _point_seg_dist(c, a, b))
    return d


def _polylines(line):
    """Every drawn polyline of a Line2D, as ``[(p0, p1), ...]`` in data units."""
    try:
        xs = line.get_xdata(orig=False)
        ys = line.get_ydata(orig=False)
    except TypeError:                              # older matplotlib
        xs, ys = line.get_xdata(), line.get_ydata()
    if xs is None or ys is None or len(xs) < 2:
        return []
    # A marker-only line ("k.", ms=3.5) draws no line: it is a dot, not an
    # obstacle.  Testing the linestyle is the reliable way to tell.
    try:
        if not line.get_linestyle() or line.get_linestyle() in ("None", "none", ""):
            return []
    except Exception:                              # noqa: BLE001 - assume drawn
        pass
    return [((float(xs[i]), float(ys[i])), (float(xs[i + 1]), float(ys[i + 1])))
            for i in range(len(xs) - 1)]


def _patch_edges(patch):
    """Outline of a Polygon/Rectangle/Circle patch as segments."""
    try:
        verts = patch.get_path().vertices
        tf = patch.get_patch_transform()
        pts = tf.transform(verts)
    except Exception:                              # noqa: BLE001 - skip it
        return []
    pts = [(float(p[0]), float(p[1])) for p in pts]
    if len(pts) < 2:
        return []
    return [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]


def obstacles(ax, include_patches=True):
    """Drawn geometry that labels should not sit on, as ``[(p0, p1), ...]``."""
    segs = []
    for line in ax.lines:
        segs.extend(_polylines(line))
    if include_patches:
        for patch in ax.patches:
            # Both filled shapes and outlines count: a solid block and a thin
            # circle are equally bad to print text on top of.
            if patch.get_visible():
                segs.extend(_patch_edges(patch))
    for coll in ax.collections:
        try:
            for path in coll.get_paths():
                pts = [(float(p[0]), float(p[1])) for p in path.vertices]
                if len(pts) >= 2:
                    segs.extend((pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts)))
        except Exception:                          # noqa: BLE001 - skip
            continue
    return segs


def labels(ax):
    """``[(artist, text), ...]`` for every real text artist on the axes.

    An empty annotation is an arrow, not a label -- ``ax.annotate("")`` creates
    a ``Text`` with no string, and treating it as a label would report every
    arrowhead as a collision.
    """
    out = []
    for t in ax.texts:
        s = t.get_text()
        if s and s.strip():
            out.append((t, s))
    return out


def audit(ax, frame=None, segments=None, skip=()):
    """Find every collision currently present on ``ax``.

    Returns a list of dicts with ``kind``, ``a``, ``b`` and ``amount`` (pixels
    of overlap, or the clearance shortfall for a line).  An empty list means
    the layout is clean.
    """
    fig = ax.figure
    # The renderer only exists after a draw, and every measurement below goes
    # through it.  Calling draw() unconditionally is cheap next to the cost of
    # measuring against a stale transform.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    if frame is None:
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        frame = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    if segments is None:
        segments = obstacles(ax)

    items = [(t, s, _rect_of(t, ax, renderer)) for t, s in labels(ax)]
    found = []

    for i in range(len(items)):
        t_i, s_i, r_i = items[i]
        for j in range(i + 1, len(items)):
            _t_j, s_j, r_j = items[j]
            area = _overlap_area(r_i, r_j)
            if area > 0:
                found.append({"kind": SEV_OVERLAP, "a": s_i, "b": s_j,
                              "amount": round(math.sqrt(area), 4)})

    for t, s, rect in items:
        if s in skip:
            continue
        for a, b in segments:
            d = _rect_seg_dist(rect, a, b)
            if d < LINE_MARGIN:
                found.append({"kind": SEV_LINE, "a": s, "b": "",
                              "amount": round(LINE_MARGIN - d, 4)})
                break

    for t, s, rect in items:
        if s in skip:
            continue
        out = (max(0.0, frame[0] - rect[0]) + max(0.0, rect[2] - frame[2])
               + max(0.0, frame[1] - rect[1]) + max(0.0, rect[3] - frame[3]))
        if out > 0:
            found.append({"kind": SEV_FRAME, "a": s, "b": "",
                          "amount": round(out, 4)})
    return found


def _score(collisions, text):
    """How badly ``text`` is misplaced, for choosing between candidates."""
    total = 0.0
    for c in collisions:
        if c["a"] != text and c["b"] != text:
            continue
        # Two labels fighting is worse than one label grazing a guide line.
        weight = {SEV_OVERLAP: 10.0, SEV_FRAME: 6.0, SEV_LINE: 1.0}[c["kind"]]
        total += weight * (1.0 + c["amount"])
    return total


def resolve(ax, rounds=4, frame=None, skip=()):
    """Nudge colliding labels apart, in place.

    Works on one label at a time: for each, try the candidate displacements and
    keep the first that strictly lowers that label's collision score.  Labels
    are never moved *into* a collision, and a label with no clear candidate is
    left exactly where it was -- a figure with a reported collision is honest,
    a figure with a silently moved label is not.

    ``skip`` exempts labels from the line and frame checks.  This matters for
    annotations that are *supposed* to touch what they describe: an angle label
    sits inside the wedge between its two rays, and "fixing" that collision
    pushes the angle outside the figure -- which was a real regression here.
    Overlap between two labels is still checked for skipped ones, because two
    pieces of text on top of each other are wrong under any convention.

    Returns ``(before, after, moved)``.
    """
    fig = ax.figure
    before = audit(ax, frame=frame, skip=skip)
    if not before:
        return before, [], []

    moved = []
    for _round in range(rounds):
        progress = False
        for artist, text in labels(ax):
            current = audit(ax, frame=frame, skip=skip)
            if not any(c["a"] == text or c["b"] == text for c in current):
                continue

            renderer = fig.canvas.get_renderer()
            rect = _rect_of(artist, ax, renderer)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            base = artist.get_position()
            best_score = _score(current, text)
            best = None

            for fx, fy in _NUDGE:
                if fx == 0.0 and fy == 0.0:
                    continue
                artist.set_position((base[0] + fx * w, base[1] + fy * h))
                fig.canvas.draw()
                now = audit(ax, frame=frame, skip=skip)
                score = _score(now, text)
                if score < best_score - 1e-9:
                    best_score = score
                    best = (base[0] + fx * w, base[1] + fy * h)

            if best is None:
                artist.set_position(base)
                continue
            artist.set_position(best)
            fig.canvas.draw()
            moved.append(text)
            progress = True

        if not progress:
            break

    after = audit(ax, frame=frame, skip=skip)
    return before, after, moved


def finish(fig, ax, out_path, rounds=4, skip=(), **savefig_kw):
    """Audit, repair, save, and return a report.

    Drop-in replacement for the ``fig.savefig`` + ``plt.close`` pair at the end
    of every figure function.  The report is meant to be returned to the tool
    caller: it says whether the published image has any label collisions, and
    if not, how many were fixed on the way there.

    ``skip`` exempts labels that are *meant* to touch their subject -- angle
    marks, dimension arrows.  See :func:`resolve`.
    """
    import matplotlib.pyplot as plt

    fig.canvas.draw()
    before, after, moved = resolve(ax, rounds=rounds, skip=skip)

    savefig_kw.setdefault("facecolor", "white")
    savefig_kw.setdefault("bbox_inches", "tight")
    fig.savefig(out_path, **savefig_kw)
    plt.close(fig)

    return {
        "collisions": len(after),
        "fixed": len(moved),
        "remaining": [{"kind": c["kind"], "label": c["a"], "with": c["b"]}
                      for c in after],
    }
