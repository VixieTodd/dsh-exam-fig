# -*- coding: utf-8 -*-
r"""Statistics: a frequency histogram with its polygon, and a scatter plot.

Both live in one module because they answer the same question in a paper: *what
does this data look like?*  A histogram shows the shape of one variable, a
scatter plot shows whether two variables move together, and a question often
asks for both about the same table.

The numbers are the point.  A histogram drawn from hard-coded bar heights would
look right and be wrong the moment a question gives a different table, so every
bar here comes from binning the actual sample -- and the sample is what the
caller passes in.
"""
import math

import numpy as np

from .. import env, layout
from . import _helpers as H

_C_BAR = "#4a90d9"
_C_EDGE = "#1a3d5c"
_C_POINT = "#c62828"
_C_FIT = "#2e7d32"


def _nice_edges(data, bins):
    """Bin edges covering ``data`` in ``bins`` equal-width intervals."""
    lo, hi = float(min(data)), float(max(data))
    if hi <= lo:
        hi = lo + 1.0
    width = (hi - lo) / float(bins)
    return [lo + i * width for i in range(bins + 1)]


def _stats(values):
    n = len(values)
    mean = sum(values) / float(n)
    var = sum((v - mean) ** 2 for v in values) / float(n)
    return n, mean, math.sqrt(var)


def histogram(samples=None, bins=6, show_polygon=True, show_normal=True,
              xlabel="数据", ylabel="频率/组距", out_path="math_histogram.png"):
    r"""Frequency histogram of ``samples`` with the frequency polygon.

    ``samples`` is the raw data, not the counts.  Binning it here is what keeps
    the bar heights and the axis labels consistent with each other: computing
    the counts by hand in the caller and passing them in would let the two
    disagree, and nothing in the picture would reveal it.

    The frequency polygon joins the *bin midpoints* at the bin frequency, which
    is why its first and last points sit on the axis at the outer edges -- the
    textbook convention that closes the polygon.
    """
    plt = env.pyplot()
    if not samples:
        # An empty list means "use the built-in sample".  ``registry.coerce``
        # hands over the declared default ``[]``, never ``None``, so the test
        # has to be on emptiness -- ``samples is None`` would never fire and the
        # figure would come out with no bars at all.
        #
        # A mildly right-skewed sample, the shape most "read the mode off the
        # histogram" questions use.  Deterministic, not random: a figure must
        # redraw identically.
        samples = [2.1, 2.4, 2.6, 2.9, 3.0, 3.1, 3.2, 3.3, 3.5, 3.6,
                   3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.5, 4.6, 4.8,
                   5.0, 5.2, 5.4, 5.7, 6.0, 6.3, 6.8]
    samples = [float(v) for v in samples]
    bins = int(bins)
    if bins < 1:
        raise ValueError("bins must be at least 1, got %d" % bins)
    if len(samples) < 2:
        raise ValueError("need at least two samples to bin, got %d"
                         % len(samples))

    edges = _nice_edges(samples, bins)
    width = edges[1] - edges[0]
    counts = [0] * bins
    for v in samples:
        idx = int((v - edges[0]) / width)
        idx = min(max(idx, 0), bins - 1)          # the max value lands in the last bin
        counts[idx] += 1

    # Frequency / class width is the density: the bar *areas* then add up to 1,
    # which is what makes a histogram comparable to the density curve drawn on
    # top of it.
    density = [c / (len(samples) * width) for c in counts]
    mids = [0.5 * (edges[i] + edges[i + 1]) for i in range(bins)]

    fig, ax = plt.subplots(figsize=(4.9, 3.4), dpi=300)
    painted = []

    y_hi = max(density) * 1.30 if max(density) > 0 else 1.0
    for i in range(bins):
        ax.add_patch(plt.Rectangle((edges[i], 0.0), width, density[i],
                                   facecolor=_C_BAR, edgecolor=_C_EDGE,
                                   lw=1.0, alpha=0.55, zorder=2))
    # The bin edges are the numbers a histogram question quotes, so the axis
    # ticks go exactly on them.  Drawing them as ``ax.text`` below the axis put
    # them outside the frame, where the audit (rightly) reported them as
    # clipped -- and the tick labels are outside the Axes anyway, which is where
    # they belong.
    ax.set_xticks(list(edges))
    ax.set_xticklabels([H.fmt(e) for e in edges])
    painted += [H.fmt(e) for e in edges]

    if show_polygon:
        # Closed at both ends: the polygon starts and ends on the axis one bin
        # width outside the outermost midpoints.
        px = [edges[0]] + mids + [edges[-1]]
        py = [0.0] + density + [0.0]
        ax.plot(px, py, color=_C_POINT, lw=1.5, marker="o", ms=3.4,
                mfc="white", mew=1.2, zorder=4)
        painted.append("polygon")

    if show_normal:
        n, mean, sd = _stats(samples)
        if sd > 0:
            xs = np.linspace(edges[0], edges[-1], 300)
            ys = (np.exp(-0.5 * ((xs - mean) / sd) ** 2)
                  / (sd * math.sqrt(2.0 * math.pi)))
            ax.plot(xs, ys, color=_C_FIT, lw=1.4, ls=(0, (6, 3)), zorder=3)
            # The mean is marked on the axis: "where is the centre" is the
            # first thing a histogram question asks.
            xbar_text = "$\\bar{x}=%s$" % H.fmt(mean, 2)
            H.dot(ax, mean, 0.0, color=_C_FIT, ms=4.6)
            ax.text(mean, 0.045 * y_hi, xbar_text,
                    fontsize=9, color=_C_FIT, ha="center", va="bottom")
            painted.append(xbar_text.strip("$"))
            # The label sits inside the plot, so the panel needs room above the
            # tallest bar for it -- hence the 1.30 factor on y_hi.
            ax.text(edges[-1], max(density) * 1.10,
                    "$s=%s$" % H.fmt(sd, 2), fontsize=9, color=_C_FIT,
                    ha="right", va="bottom")
            painted.append("s=%s" % H.fmt(sd, 2))

    ax.set_xlim(edges[0] - 0.35 * width, edges[-1] + 0.35 * width)
    ax.set_ylim(0.0, y_hi)
    ax.set_xlabel(xlabel, fontsize=10.5)
    ax.set_ylabel(ylabel, fontsize=10.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(labelsize=8.5)
    # The axis labels are *outside* the Axes, and the default bottom margin is
    # 0.11 of the figure -- not enough for a tick label plus an x label, so the
    # x label was clipped by the page edge.  Reserving the margin here is the
    # only place it can be done: after this the viewport is measured and frozen.
    fig.subplots_adjust(bottom=0.20, left=0.16, right=0.97, top=0.96)

    n, mean, sd = _stats(samples)
    report = layout.finish(fig, ax, out_path,
                           skip=(xlabel, ylabel, "$\\bar{x}=%s$" % H.fmt(mean, 2),
                                 "$s=%s$" % H.fmt(sd, 2) if show_normal else ""))
    return {
        "n": n,
        "mean": mean,
        "std": sd,
        "bin_edges": edges,
        "counts": counts,
        "bin_width": width,
        "mode_bin": edges[counts.index(max(counts))],
        "marks": set(painted),
        "layout": report,
    }


def scatter(points=None, slope=0.0, intercept=0.0, show_fit=True,
            xlabel="$x$", ylabel="$y$", out_path="math_scatter.png"):
    r"""Scatter plot of ``points`` with an optional least-squares line.

    ``points`` is a list of ``[x, y]`` pairs.  When ``show_fit`` is on, the line
    is the *computed* regression, not ``slope``/``intercept`` -- those two only
    describe the line when the caller passes a synthetic cloud and wants the
    figure to match a stated model.  If a question gives ``y = 2x + 1``, pass
    those; if it gives a table, leave them and read the fit back off the result.
    """
    plt = env.pyplot()
    if not points:
        # Same empty-default trap as ``histogram``: coerce supplies ``[]``.
        # A positive, moderately tight cloud -- the shape a "正相关" question
        # uses.  Fixed values so the figure is reproducible.
        points = [[1.0, 2.3], [1.6, 3.1], [2.2, 3.4], [2.8, 4.6], [3.3, 4.9],
                  [3.9, 5.7], [4.4, 6.2], [5.0, 6.4], [5.6, 7.3], [6.2, 7.9]]
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) < 2:
        raise ValueError("need at least two points, got %d" % len(pts))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    fig, ax = plt.subplots(figsize=(4.6, 3.5), dpi=300)
    painted = []

    # Least squares, computed rather than taken from the parameters: the whole
    # point of a scatter plot is that the line comes from the data.
    n = float(len(pts))
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in pts)
    if sxx <= 0:
        raise ValueError("all points share the same x: no regression line exists")
    k = sxy / sxx
    b0 = my - k * mx
    r_num = sxy
    r_den = math.sqrt(sxx * sum((y - my) ** 2 for y in ys))
    corr = r_num / r_den if r_den > 0 else 0.0

    x_lo = min(xs) - 0.55
    x_hi = max(xs) + 0.55
    y_lo = min(ys) - 0.55
    y_hi = max(ys) + 0.75

    if show_fit:
        ax.plot([x_lo, x_hi], [k * x_lo + b0, k * x_hi + b0],
                color=_C_FIT, lw=1.5, zorder=2)
        ax.text(x_hi - 0.05, k * x_hi + b0 + 0.22,
                "$\\hat{y}=%sx+%s$" % (H.fmt(k, 2), H.fmt(b0, 2)),
                fontsize=9.5, color=_C_FIT, ha="right", va="bottom")
        painted.append("yhat=%sx+%s" % (H.fmt(k, 2), H.fmt(b0, 2)))

    ax.plot(xs, ys, "o", ms=5.0, color=_C_POINT, mec="white", mew=0.8,
            zorder=4, ls="none")
    # The dots are the data, not a label: nothing is written for them, so they
    # are not a mark.  (A mark with no text behind it is the one thing the
    # "marks come from the drawing" contract forbids.)

    # The correlation coefficient belongs on the picture: it is the number the
    # question asks for, and printing it makes the figure checkable.
    ax.text(x_lo + 0.08, y_hi - 0.18, "$r=%s$" % H.fmt(corr, 3),
            fontsize=9.5, color="#37474f", ha="left", va="top")
    painted.append("r=%s" % H.fmt(corr, 3))

    painted += H.frame(ax, (x_lo, x_hi), (y_lo, y_hi),
                       xlabel=xlabel, ylabel=ylabel, origin=False,
                       style="corner")
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    report = layout.finish(fig, ax, out_path, skip=H.FRAME_LABELS)
    return {
        "n": int(n),
        "slope": k,
        "intercept": b0,
        "correlation": corr,
        "marks": set(painted),
        "layout": report,
    }
