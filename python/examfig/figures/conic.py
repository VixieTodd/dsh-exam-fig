# -*- coding: utf-8 -*-
r"""Conic sections: ellipse, hyperbola and parabola with their focal data.

The three curves are one function because they are one topic.  A question that
says "the ellipse x^2/9 + y^2/4 = 1" and a question that says "the parabola
y^2 = 4x" are asking the reader to do the same thing: locate the focus, and
read the directrix off the same picture.  Keeping them in one place means the
focus/directrix construction cannot drift apart between them.

Every number here is *derived*: the focus is computed from (a, b), the
directrix from c and a, and the curve is sampled from the same relation that
produced those numbers.  Nothing is placed by eye.
"""
import math

import numpy as np

from .. import env, layout
from . import _helpers as H

# Colour per conic, so a figure that shows two of them stays readable.
_C_ELLIPSE = "#1565c0"
_C_HYPER = "#c62828"
_C_PARAB = "#2e7d32"


def _ellipse(a, b, n=800):
    t = np.linspace(0.0, 2.0 * math.pi, n)
    return a * np.cos(t), b * np.sin(t)


def _hyperbola(a, b, n=800):
    """Right branch and left branch, each sampled separately.

    Sampling ``cosh`` over a single range and joining the two branches would
    draw a straight line across the gap between them -- the classic
    "hyperbola with a bar through the middle" defect.
    """
    lim = math.acosh(max(1.35, a / b * 1.35))
    t = np.linspace(-lim, lim, n)
    right = (a * np.cosh(t), b * np.sinh(t))
    left = (-a * np.cosh(t), b * np.sinh(t))
    return right, left


def conic(kind="ellipse", a=3.0, b=2.0, p=2.0, show_directrix=True,
          show_asymptotes=True, span=None, out_path="math_conic.png"):
    r"""Draw one conic with its focus (foci) and directrix.

    ``kind`` is ``ellipse``, ``hyperbola`` or ``parabola``.

    * ellipse: ``x^2/a^2 + y^2/b^2 = 1``; ``c = sqrt(a^2 - b^2)``
    * hyperbola: ``x^2/a^2 - y^2/b^2 = 1``; ``c = sqrt(a^2 + b^2)``
    * parabola: ``y^2 = 2 p x``; focus ``(p/2, 0)``, directrix ``x = -p/2``

    For the parabola ``a`` and ``b`` are ignored; for the ellipse and
    hyperbola ``p`` is.  That is deliberate: a caller filling in the prose's
    numbers should be able to pass all three without knowing which curve the
    figure picked, and the unused ones simply do not appear.
    """
    plt = env.pyplot()
    kind = str(kind).lower()
    a, b, p = abs(float(a)), abs(float(b)), abs(float(p))
    if kind not in ("ellipse", "hyperbola", "parabola"):
        raise ValueError("kind must be ellipse, hyperbola or parabola, got %r"
                         % (kind,))
    if kind != "parabola" and (a <= 0 or b <= 0):
        raise ValueError("a and b must be positive, got a=%g b=%g" % (a, b))
    if kind == "parabola" and p <= 0:
        raise ValueError("p must be positive for y^2 = 2 p x, got p=%g" % p)

    fig, ax = plt.subplots(figsize=(4.6, 3.8), dpi=300)
    painted = []

    if kind == "ellipse":
        c = math.sqrt(max(a * a - b * b, 0.0))
        xs, ys = _ellipse(a, b)
        ax.plot(xs, ys, color=_C_ELLIPSE, lw=2.0, zorder=3)
        color = _C_ELLIPSE
        foci = [(-c, 0.0), (c, 0.0)]
        directrices = [(-a * a / c, 0.0), (a * a / c, 0.0)] if c > 0 else []
        x_lo, x_hi = -a - 1.0, a + 1.0
        y_lo, y_hi = -b - 0.85, b + 0.85
    elif kind == "hyperbola":
        c = math.sqrt(a * a + b * b)
        right, left = _hyperbola(a, b)
        for xs, ys in (right, left):
            ax.plot(xs, ys, color=_C_HYPER, lw=2.0, zorder=3)
        color = _C_HYPER
        foci = [(-c, 0.0), (c, 0.0)]
        directrices = [(-a * a / c, 0.0), (a * a / c, 0.0)]
        if show_asymptotes:
            # The asymptotes are what makes a hyperbola readable: without them
            # the two branches look like a pair of unrelated arcs.
            t = max(a, b) * 1.9
            for sgn in (-1.0, 1.0):
                H.guide(ax, (-t, sgn * b / a * -t), (t, sgn * b / a * t),
                        color="#9e9e9e")
            painted += ["asymptote"]
        x_lo, x_hi = -c - 1.2, c + 1.2
        y_lo, y_hi = -c * b / a - 0.9, c * b / a + 0.9
    else:
        c = p / 2.0
        # y^2 = 2 p x  =>  x = y^2 / (2p)
        y_span = max(2.0 * p, 2.6)
        ys = np.linspace(-y_span, y_span, 900)
        xs = ys ** 2 / (2.0 * p)
        ax.plot(xs, ys, color=_C_PARAB, lw=2.0, zorder=3)
        color = _C_PARAB
        foci = [(c, 0.0)]
        directrices = [(-c, 0.0)]
        x_lo, x_hi = -c - 1.0, max(xs) + 0.6
        y_lo, y_hi = -y_span - 0.6, y_span + 0.6

    if span:
        x_lo, x_hi, y_lo, y_hi = (float(v) for v in span)

    painted += H.frame(ax, (x_lo, x_hi), (y_lo, y_hi))

    # -- foci -------------------------------------------------------------
    # A focus on the x-axis sits *on* the axis stroke, so its dot is drawn on
    # top of it (zorder) and the letter is pushed up: printed below, it would
    # be crossed by the axis arrow.
    for i, (fx, fy) in enumerate(foci, start=1):
        H.dot(ax, fx, fy, color=color, ms=5.2)
        name = "$F_%d$" % i if len(foci) > 1 else "$F$"
        ax.text(fx, fy + 0.30, name, fontsize=11, color=color,
                ha="center", va="bottom")
        painted.append(name.strip("$"))
    if len(foci) > 1:
        painted.append("F")
    ax.text(0.0, -0.30, "$O$", fontsize=10, ha="center", va="top")
    painted.append("O")

    # -- directrix --------------------------------------------------------
    if show_directrix:
        for dx, _dy in directrices:
            ax.plot([dx, dx], [y_lo, y_hi], color="#8e24aa", lw=1.3,
                    ls=(0, (5, 3)), zorder=2)
            ax.text(dx, y_lo + 0.22 * (y_hi - y_lo), "$l$", fontsize=10.5,
                    color="#8e24aa", ha="center", va="bottom")
        painted.append("l")

    # -- the defining lengths --------------------------------------------
    # "a", "b", "c" are the numbers the question actually gives, so they get
    # printed on the picture: a reader checking x^2/9 + y^2/4 = 1 wants to see
    # the 3 and the 2, not just a plausible-looking oval.
    if kind == "ellipse":
        ax.annotate("", xy=(a, 0), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="<|-|>", color="#455a64",
                                    lw=1.0, mutation_scale=9), zorder=4)
        ax.text(a * 0.5, 0.22, "$a=%s$" % H.fmt(a), fontsize=9.5,
                color="#455a64", ha="center", va="bottom")
        ax.annotate("", xy=(0, b), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="<|-|>", color="#455a64",
                                    lw=1.0, mutation_scale=9), zorder=4)
        ax.text(0.16, b * 0.55, "$b=%s$" % H.fmt(b), fontsize=9.5,
                color="#455a64", ha="left", va="center")
        painted += ["a=%s" % H.fmt(a), "b=%s" % H.fmt(b)]
    elif kind == "hyperbola":
        ax.annotate("", xy=(a, 0), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="<|-|>", color="#455a64",
                                    lw=1.0, mutation_scale=9), zorder=4)
        ax.text(a * 0.5, 0.22, "$a=%s$" % H.fmt(a), fontsize=9.5,
                color="#455a64", ha="center", va="bottom")
        painted.append("a=%s" % H.fmt(a))
    else:
        # y^2 = 2 p x: p is the one number the equation gives, so it goes on the
        # picture -- drawn from the origin out to the focus distance, which is
        # exactly p/2 = c.
        H.dot(ax, 0.0, 0.0, color=color, ms=4.0)
        ax.annotate("", xy=(c, 0.0), xytext=(0.0, 0.0),
                    arrowprops=dict(arrowstyle="<|-|>", color="#455a64",
                                    lw=1.0, mutation_scale=9), zorder=4)
        ax.text(c * 0.5, -0.34, "$p=%s$" % H.fmt(p), fontsize=9.5,
                color="#455a64", ha="center", va="top")
        painted.append("p=%s" % H.fmt(p))

    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(y_lo, y_hi)
    ax.axis("off")
    report = layout.finish(fig, ax, out_path,
                           skip=H.FRAME_LABELS + ("$F_1$", "$F_2$", "$F$"))

    return {
        "kind": kind,
        "a": a if kind != "parabola" else None,
        "b": b if kind != "parabola" else None,
        "p": p if kind == "parabola" else None,
        "c": c,
        "eccentricity": (c / a) if kind != "parabola" else 1.0,
        "foci": foci,
        "directrix_x": [d[0] for d in directrices],
        "marks": set(painted),
        "layout": report,
    }
