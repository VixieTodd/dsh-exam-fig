# -*- coding: utf-8 -*-
"""Shared drawing primitives for the figure modules.

Several figures in this package draw the same things: a coordinate frame with
arrowheads, a number printed the way a textbook prints it, a dot with its
value, a dimension bracket.  They live here for one reason -- a defect in any
of them would otherwise appear in every figure that re-implements it, and
there would be no single place to fix it.

The convention that matters: **every label painted here is returned to the
caller**, so a drawing function can add it to its ``marks`` without ever
re-reading the rendered image.
"""
import math

# Axis names and the origin.  Every figure with a coordinate frame paints
# these three, and each is *meant* to touch the stroke it names, so the
# collision audit is told to skip them by name.
FRAME_LABELS = ("$x$", "$y$", "$O$")


def fmt(value, digits=3):
    """Short numeric label: ``2``, ``-1.5``, ``0.333``.

    Trailing zeros are stripped because a textbook writes ``1.5``, not
    ``1.500``, and the label is read as a value, not as a measurement.
    """
    v = float(value)
    if not math.isfinite(v):
        return ""
    if abs(v - round(v)) < 1e-9:
        return "%d" % int(round(v))
    out = ("%." + str(int(digits)) + "f") % v
    out = out.rstrip("0").rstrip(".")
    return "0" if out in ("-0", "") else out


def frame(ax, xlim, ylim, xlabel="$x$", ylabel="$y$", origin=True,
          style="center", zorder=5):
    """Draw the two axis arrows; return the labels painted.

    ``style="center"`` puts the origin inside the picture -- the shape of a
    parabola or a sine curve is read against the origin, so it must be visible.

    ``style="corner"`` puts the axes on the left and bottom edges, for graphs
    whose origin *is* the corner (``x-t``, ``p-V``, titration).  Drawing a
    centred origin there would put the curve on top of the axis.
    """
    x0, x1 = float(xlim[0]), float(xlim[1])
    y0, y1 = float(ylim[0]), float(ylim[1])
    w, h = x1 - x0, y1 - y0
    painted = []
    arrow_kw = dict(arrowstyle="-|>", color="k", lw=1.2,
                    mutation_scale=11, shrinkA=0, shrinkB=0)

    if style == "corner":
        ax.annotate("", xy=(x1, y0), xytext=(x0, y0), arrowprops=arrow_kw,
                    zorder=zorder)
        ax.annotate("", xy=(x0, y1), xytext=(x0, y0), arrowprops=arrow_kw,
                    zorder=zorder)
        ax.text(x1, y0 - 0.045 * h, xlabel, fontsize=10.5, ha="right", va="top")
        ax.text(x0 - 0.012 * w, y1, ylabel, fontsize=10.5, ha="right", va="top")
        painted += [xlabel, ylabel]
        if origin:
            ax.text(x0 - 0.012 * w, y0 - 0.045 * h, "$O$", fontsize=10,
                    ha="right", va="top")
            painted.append("$O$")
        return painted

    ax.annotate("", xy=(x1 - 0.015 * w, 0), xytext=(x0 + 0.015 * w, 0),
                arrowprops=arrow_kw, zorder=zorder)
    ax.annotate("", xy=(0, y1 - 0.015 * h), xytext=(0, y0 + 0.015 * h),
                arrowprops=arrow_kw, zorder=zorder)
    ax.text(x1 - 0.01 * w, 0.022 * h, xlabel, fontsize=10.5, ha="right",
            va="bottom")
    ax.text(0.014 * w, y1 - 0.01 * h, ylabel, fontsize=10.5, ha="left", va="top")
    painted += [xlabel, ylabel]
    if origin:
        ax.text(-0.012 * w, -0.022 * h, "$O$", fontsize=10, ha="right", va="top")
        painted.append("$O$")
    return painted


def fit_viewport(ax, fig, xs, ys, pad_frac=0.10, min_pad=2.0, base_h=3.0,
                 max_w=9.0, min_w=3.2):
    """Frame exactly the points the drawing occupies, and shape the page to it.

    Ray diagrams are the case this exists for.  ``u < f`` forms a *virtual*
    image whose distance is a large multiple of the object distance, so a
    viewport built from ``u`` alone cuts the image -- and the ``A'B'`` label
    that names it -- clean off the page.  Taking the extremes of the real
    geometry keeps every marked point inside the frame.

    With ``aspect="equal"`` a fixed-size page would then squash such a drawing
    into a hairline, so the page width follows the data aspect instead: the
    geometry stays exact and the labels keep their size relative to it.

    Returns ``(x_lo, x_hi, y_lo, y_hi)``; the caller sets the limits itself.
    """
    xs = [float(v) for v in xs]
    ys = [float(v) for v in ys]
    if not xs or not ys:
        raise ValueError("fit_viewport needs at least one x and one y")
    x_lo, x_hi = min(xs), max(xs)
    y_lo, y_hi = min(ys), max(ys)
    span_x = x_hi - x_lo
    span_y = y_hi - y_lo
    pad_x = max(min_pad, pad_frac * span_x)
    pad_y = max(min_pad * 0.6, pad_frac * span_y)
    x_lo, x_hi = x_lo - pad_x, x_hi + pad_x
    y_lo, y_hi = y_lo - pad_y, y_hi + pad_y
    span_x, span_y = x_hi - x_lo, y_hi - y_lo
    if span_x > 0 and span_y > 0:
        want_w = base_h * span_x / span_y
        fig.set_size_inches(min(max_w, max(min_w, want_w)), base_h)
    return x_lo, x_hi, y_lo, y_hi


def dot(ax, x, y, filled=True, color="k", ms=5.0, zorder=6):
    """A marked point.  Hollow means "not included", filled means "included"."""
    if filled:
        ax.plot(x, y, "o", ms=ms, color=color, zorder=zorder,
                markeredgewidth=0)
    else:
        ax.plot(x, y, "o", ms=ms, color="white", markeredgecolor=color,
                markeredgewidth=1.4, zorder=zorder)


def arrow(ax, p0, p1, color="#1a1a1a", lw=1.6, zorder=6, style="-|>",
          shrink=0.0, scale=12):
    """A single arrow from ``p0`` to ``p1``."""
    ax.annotate("", xy=tuple(p1), xytext=tuple(p0),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw,
                                shrinkA=shrink, shrinkB=shrink,
                                mutation_scale=scale),
                zorder=zorder)


def bracket(ax, p0, p1, text=None, color="#555", lw=1.1, fontsize=9.5,
            text_off=(0.0, 0.0), ha="center", va="center", zorder=6,
            style="<|-|>"):
    """A double-headed measure between two points, with optional text.

    Used for a period, a wavelength, a chord, a distance -- anything the
    question asks the reader to read off as a length rather than as a value on
    an axis.
    """
    arrow(ax, p0, p1, color=color, lw=lw, zorder=zorder, style=style, scale=10)
    if not text:
        return None
    mx = 0.5 * (p0[0] + p1[0]) + text_off[0]
    my = 0.5 * (p0[1] + p1[1]) + text_off[1]
    return ax.text(mx, my, text, fontsize=fontsize, color=color,
                   ha=ha, va=va, zorder=zorder)


def guide(ax, p0, p1, color="#9e9e9e", lw=1.0, zorder=2, dashes=(4, 3)):
    """A dashed construction line: an asymptote, a projection, an axis of symmetry."""
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], ls=(0, dashes), color=color,
            lw=lw, zorder=zorder)


def offset_text(ax, xy, text, dx_pt=0.0, dy_pt=0.0, **kw):
    """Text a fixed number of *points* from a data anchor.

    A label offset written in data units breaks as soon as a parameter shrinks
    the drawing: the offset scales with the data span while the glyphs do not,
    so a label that cleared the frame at ``rod_length=1.0`` lands outside it at
    ``0.2``.  Offsets in points keep the gap between the label and the thing it
    names constant, whatever the scale.
    """
    kw.setdefault("zorder", 8)
    return ax.annotate(text, xy=tuple(xy), xytext=(dx_pt, dy_pt),
                       textcoords="offset points", **kw)


def shrink_colliding(fig, ax, skip=(), floor=5.5, step=0.88, rounds=26):
    """Shrink any label that still crosses a line or leaves the frame.

    This is the last resort after placement: when a drawing is small enough that
    a label has nowhere to go, the honest fix is smaller type rather than a
    label printed on top of the rails.  Only labels the audit actually flags are
    touched, so a figure with room to spare is unchanged.

    Must run *after* the viewport is final.  A label's box in data units depends
    on the axis scale, so shrinking the viewport afterwards would undo the fit.
    """
    from .. import layout

    shrunk = []
    for _ in range(rounds):
        found = layout.audit(ax, skip=skip)
        if not found:
            break
        targets = []
        for c in found:
            if c["kind"] == layout.SEV_OVERLAP:
                continue
            if c["a"] not in targets:
                targets.append(c["a"])
        if not targets:
            break
        progress = False
        by_text = {s: t for t, s in layout.labels(ax)}
        for name in targets:
            artist = by_text.get(name)
            if artist is None:
                continue
            fs = artist.get_fontsize()
            if fs <= floor + 1e-9:
                continue
            artist.set_fontsize(max(floor, fs * step))
            shrunk.append(name)
            progress = True
        if not progress:
            break
    return shrunk


def fit_text(ax, fig, artist, max_w=None, max_h=None, floor=5.5):
    """Shrink ``artist``'s font until its measured box fits the given limits.

    ``fit_fontsize`` solves for a height from the axis scale, which is enough
    when the constraint is a band.  When the constraint is a *box* -- "this
    label must stay between the left rail and the arrow head" -- the rendered
    width matters and only a measurement answers it.  Text width is not a
    multiple of the font size in general (mathtext, subscripts), so this
    measures and iterates instead of scaling by formula.
    """
    from .. import layout

    for _ in range(14):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        rect = layout._rect_of(artist, ax, renderer)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        over = []
        if max_w is not None and w > max_w:
            over.append(max_w / w if w > 0 else 1.0)
        if max_h is not None and h > max_h:
            over.append(max_h / h if h > 0 else 1.0)
        if not over:
            return artist.get_fontsize()
        fs = artist.get_fontsize()
        nxt = fs * max(0.55, min(0.96, min(over)))
        if nxt <= floor:
            artist.set_fontsize(floor)
            return floor
        artist.set_fontsize(nxt)
    return artist.get_fontsize()


def fit_fontsize(ax, fig, span, frac=0.55, base=9.5, floor=6.0, axis="y"):
    """Largest font whose glyph size stays under ``frac * span`` data units.

    A label inside a narrow band (the gap between two rails, say) has to be
    shorter than the band.  The glyph size is fixed in points while the band is
    fixed in data units, so the two only agree at one scale; this solves for the
    font instead of hoping the scale is convenient.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bbox = ax.get_window_extent(renderer)
    lo, hi = (ax.get_xlim() if axis == "x" else ax.get_ylim())
    span_px = bbox.width if axis == "x" else bbox.height
    if abs(hi - lo) <= 0 or span_px <= 0:
        return base
    px_per_unit = span_px / abs(hi - lo)
    at_base = base * fig.dpi / 72.0 / px_per_unit
    if at_base <= frac * span:
        return base
    return max(floor, base * (frac * span) / at_base)


def points_per_unit(ax, fig, axis="x"):
    """How many points one data unit spans, for writing offsets in data terms."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bbox = ax.get_window_extent(renderer)
    if axis == "x":
        lo, hi = ax.get_xlim()
        span_px = bbox.width
    else:
        lo, hi = ax.get_ylim()
        span_px = bbox.height
    span = abs(hi - lo)
    if span <= 0 or span_px <= 0:
        return 1.0
    return (span_px / span) * 72.0 / fig.dpi


def pad_thin_axes(fig, ax, min_ratio=0.45):
    """Keep a very flat or very tall drawing from becoming a hairline.

    With ``aspect="equal"`` matplotlib shrinks the axes to the data's aspect
    ratio.  A rod of 0.2 m on 3 m rails is genuinely a thin sliver, so the axes
    collapses to 85 px tall and a 9.5 pt label -- 40 px at 300 dpi -- is half
    the height of the drawing.  Padding the short axis with blank margin keeps
    the geometry exact (equal aspect is preserved) while giving the labels
    somewhere to live.
    """
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    if dx <= 0 or dy <= 0:
        return
    w_in, h_in = fig.get_size_inches()
    want = dx * (h_in / w_in) * min_ratio
    if dy >= want:
        return
    mid = 0.5 * (y0 + y1)
    half = 0.5 * want
    ax.set_ylim(mid - half, mid + half)


def expand_to_fit(fig, ax, pad_pt=3.0, rounds=10, tol=1e-4):
    """Grow the viewport until every label box lies inside it.

    Point-based offsets still need somewhere to go: if the axes is only a few
    points tall, a label placed six points below the drawing is outside the
    frame no matter how it is anchored.  This measures the real rendered boxes
    and grows the limits until they fit, iterating because enlarging the limits
    shrinks the labels' size in data units.

    Must run *before* ``layout.finish``: the audit measures through
    ``transData``, so any later ``set_xlim`` would invalidate every box.
    """
    from .. import layout

    pad = pad_pt * fig.dpi / 72.0
    for _ in range(rounds):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        rects = [layout._rect_of(t, ax, renderer) for t, _s in layout.labels(ax)]
        if not rects:
            return True
        nx0 = min([x0] + [r[0] for r in rects])
        nx1 = max([x1] + [r[2] for r in rects])
        ny0 = min([y0] + [r[1] for r in rects])
        ny1 = max([y1] + [r[3] for r in rects])
        if (abs(nx0 - x0) < tol * (x1 - x0) and abs(nx1 - x1) < tol * (x1 - x0)
                and abs(ny0 - y0) < tol * (y1 - y0)
                and abs(ny1 - y1) < tol * (y1 - y0)):
            return True
        px_per_x = ax.get_window_extent(renderer).width / (x1 - x0)
        px_per_y = ax.get_window_extent(renderer).height / (y1 - y0)
        ax.set_xlim(nx0 - pad / px_per_x, nx1 + pad / px_per_x)
        ax.set_ylim(ny0 - pad / px_per_y, ny1 + pad / px_per_y)
    return False


def ticks(ax, x0, x1, y=0.0, length=0.10, max_count=26):
    """Short tick marks along a horizontal axis; returns the values drawn."""
    lo = int(math.ceil(min(x0, x1) - 1e-9))
    hi = int(math.floor(max(x0, x1) + 1e-9))
    if hi - lo + 1 > max_count:
        return []
    vals = list(range(lo, hi + 1))
    for v in vals:
        ax.plot([v, v], [y - length, y + length], color="#1a1a1a", lw=1.0,
                zorder=3)
    return vals


def finish_panels(fig, axes, out_path, skip=()):
    """``layout.finish`` for a figure with more than one panel.

    ``layout.finish`` audits a single Axes.  A two-panel figure that passes only
    the left one therefore publishes the right panel with no collision check at
    all -- the labels there can overlap freely and the report still says
    ``collisions: 0``.  This resolves every extra panel first and then hands the
    first one to ``layout.finish``, which does the measuring and the saving, so
    the returned report covers every label on the page.
    """
    from .. import layout

    axes = list(axes)
    extra_before, extra_after, extra_moved = [], [], []
    for ax in axes[1:]:
        before, after, moved = layout.resolve(ax, skip=skip)
        extra_before.extend(before)
        extra_after.extend(after)
        extra_moved.extend(moved)

    report = layout.finish(fig, axes[0], out_path, skip=skip)
    report["collisions"] += len(extra_after)
    report["fixed"] += len(extra_moved)
    report["remaining"].extend(
        {"kind": c["kind"], "label": c["a"], "with": c["b"]}
        for c in extra_after)
    return report
