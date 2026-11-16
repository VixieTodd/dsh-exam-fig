# -*- coding: utf-8 -*-
r"""Kinematics graphs: ``x-t`` beside ``v-t``, both from one motion.

The two panels are not independent pictures -- they describe the same body.
Drawing them from separate parameters invites the classic error of a ``v-t``
graph whose area does not equal the displacement shown in ``x-t``.  Here a
single motion is described once (initial position, initial velocity,
acceleration), and both curves are computed from it, so the relation

    x(t) = x0 + v0 t + a t**2 / 2,      v(t) = v0 + a t

holds by construction.  The area under ``v-t`` up to ``t_end`` is printed as a
number so a question can quote it, and it is asserted equal to ``x(t_end)-x0``.

The zero crossing of ``v`` is marked on both panels with a dashed guide: that is
where the object reverses, and it is the single most-asked fact about these
graphs.  If ``v`` never changes sign in the window, nothing is marked -- a
made-up turning point would be worse than none.

The panels are tagged ``x-t`` and ``v-t`` rather than 甲/乙: the tags are read
without a legend, and ASCII keeps the labels out of the CJK font path where a
missing glyph would silently render as an empty box.
"""
import numpy as np

from .. import env
from . import _helpers as H
_C_POS = "#1565c0"
_C_VEL = "#c62828"


def motion(x0=0.0, v0=6.0, a=-2.0, t_end=0.0, show_area=True,
           out_path="phys_motion.png"):
    r"""Position-time and velocity-time graphs of one uniformly accelerated motion.

    ``t_end=0`` picks a window that runs a little past the turning point, which
    is the window a question about "when does it reverse" is read from.

    Returns ``x`` and ``v`` at ``t_end``, the displacement, the turning time
    (``None`` when the velocity never reverses) and the area under ``v-t``.
    """
    plt = env.pyplot()
    x0, v0, a = float(x0), float(v0), float(a)
    t_end = float(t_end)
    if t_end <= 0:
        turn = (-v0 / a) if abs(a) > 1e-12 and v0 * a < 0 else None
        t_end = (1.6 * turn) if turn else 4.0
    if t_end <= 0:
        raise ValueError("t_end must be positive")

    t = np.linspace(0.0, t_end, 700)
    x = x0 + v0 * t + 0.5 * a * t * t
    v = v0 + a * t

    t_turn = None
    if abs(a) > 1e-12:
        cand = -v0 / a
        if 1e-9 < cand < t_end:
            t_turn = float(cand)

    area = float(v0 * t_end + 0.5 * a * t_end * t_end)
    assert abs(area - (x[-1] - x0)) < 1e-6 * max(1.0, abs(area)), \
        "the area under v-t must equal the displacement"

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), dpi=300)
    painted = []

    def _panel(ax, ys, colour, ylabel, tag):
        y_lo = min(float(ys.min()), 0.0)
        y_hi = max(float(ys.max()), 0.0)
        span = max(y_hi - y_lo, 1e-6)
        y_lo -= 0.18 * span
        y_hi += 0.18 * span
        painted.extend(H.frame(ax, (-0.06 * t_end, 1.10 * t_end), (y_lo, y_hi),
                               xlabel="$t$", ylabel=ylabel, style="corner"))
        ax.text(0.98, 0.96, tag, transform=ax.transAxes, fontsize=10.5,
                ha="right", va="top", color="#455a64")
        painted.append(tag)
        ax.plot(t, ys, color=colour, lw=2.0, zorder=5)
        return y_lo, y_hi

    y_lo, y_hi = _panel(axes[0], x, _C_POS, "$x$", "x-t")
    v_lo, v_hi = _panel(axes[1], v, _C_VEL, "$v$", "v-t")

    # Shade the area under v-t: it *is* the displacement, and a reader who sees
    # the shading reads the integral without being told.
    if show_area:
        axes[1].fill_between(t, 0.0, v, color=_C_VEL, alpha=0.13, zorder=2)
        txt = "S=%s" % H.fmt(area, 2)
        axes[1].text(0.55 * t_end, 0.04 * (v_hi - v_lo), "$%s$" % txt,
                     fontsize=9.5, color=_C_VEL, ha="center", va="bottom")
        painted.append(txt)

    if t_turn is not None:
        x_turn = x0 + v0 * t_turn + 0.5 * a * t_turn ** 2
        for ax, lo, hi in ((axes[0], y_lo, y_hi), (axes[1], v_lo, v_hi)):
            H.guide(ax, (t_turn, lo), (t_turn, hi))
        H.dot(axes[0], t_turn, x_turn, filled=True, color=_C_POS, ms=4.4)
        H.dot(axes[1], t_turn, 0.0, filled=True, color=_C_VEL, ms=4.4)
        axes[1].text(t_turn, 0.06 * (v_hi - v_lo), "$t=%s$" % H.fmt(t_turn, 2),
                     fontsize=9, color="#37474f", ha="center", va="bottom")
        painted.append("t=%s" % H.fmt(t_turn, 2))

    # The value at the end of the window, so the numbers in the question can be
    # checked against the picture.
    txt = H.fmt(x[-1], 2)
    axes[0].text(t_end, x[-1], "$%s$" % txt, fontsize=9, color=_C_POS,
                 ha="left", va="center")
    painted.append(txt)

    fig.tight_layout()
    report = H.finish_panels(fig, axes, out_path,
                             skip=("$t$", "$x$", "$v$", "$O$", "x-t", "v-t"))

    return {
        "x_end": float(x[-1]), "v_end": float(v[-1]),
        "displacement": float(x[-1] - x0), "area": area,
        "turning_time": t_turn,
        "marks": set(painted), "layout": report,
    }
